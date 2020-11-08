# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import datetime


class Request(models.Model):
    _name = 'lean.request'
    _inherit = 'mail.thread'
    description = fields.Text(required=True)
    state = fields.Selection([
        ('draft', 'Draft')
        , ('review', 'Under Review')
        , ('in_progress', 'In Progress')
        , ('completed', 'Completed')
    ], default='draft')

    tracker_tag = fields.Selection([
        ('on_track', 'On Track')
        , ('due_soon', 'Due Soon')
        , ('over_due', 'Over Due')

    ])

    def notify(self, state):
        admin = self.env['res.users'].browse(2)
        if state == 'review':
            my_group = self.env['res.groups'].search([('name', '=', 'Service Responsible')])
            users_to_notify = my_group.users

            notification_ids = []
            for user in users_to_notify.mapped('partner_id').ids:
                notification_ids.append((0, 0, {
                    'res_partner_id': user,
                    'notification_type': 'inbox'}))

            # Internal Messages
            self.sudo().message_post(
                subject='New Request',
                body='A new request has been submitted.'
                , message_type='notification'
                , notification_ids=notification_ids
                , subtype="mail.mt_comment"
                , author_id=self.env.user.partner_id.id,
            )

            # Web Notify
            for user in users_to_notify:
                user.with_user(admin).notify_info('A new request has been submitted.')

        if state == 'completed':
            # Internal Message
            notification_ids = []
            notification_ids.append((0, 0, {
                'res_partner_id': self.create_uid.partner_id.id,
                'notification_type': 'inbox'}))
            self.sudo().message_post(
                subject='Request Completed',
                body='Your request has been completed.'
                , message_type='notification'
                , notification_ids=notification_ids
                , subtype="mail.mt_comment"
                , author_id=self.env.user.partner_id.id,
            )

            # Web Notify
            self.create_uid.with_user(admin).notify_info('Your request has been completed.')

    def create_reminder_once(self):
        # Reminders
        message = "Please Review the request"
        model_id = self.env['ir.model'].sudo().search([('name', '=', 'lean.request')])
        my_code = f"model.reminder({self.id}, '{message}')"
        next_call = datetime.datetime.now() + datetime.timedelta(minutes=2)

        my_job = {
            'nextcall': next_call
            , 'priority': 1
            , 'numbercall': 1
            , 'interval_type': 'minutes'
            , 'interval_number': 1
            , 'model_id': model_id.id
            , 'state': 'code'
            , 'code': my_code
            , 'name': f'Request Reminder - One Time ({self.id})'
            , 'user_id': 1
        }
        my_cron = self.env['ir.cron'].sudo()
        my_cron.create(my_job)
        id1 = my_cron.search([('id', '=', 1)])

    def create_reminder_recurring(self):
        # Reminders
        message = "Please submit the request."
        model_id = self.env['ir.model'].sudo().search([('name', '=', 'lean.request')])
        my_code = f"model.reminder({self.id},'{message}')"
        next_call = datetime.datetime.now() + datetime.timedelta(minutes=5)
        my_job = {
            'nextcall': next_call
            , 'priority': 1
            , 'numbercall': -1
            , 'interval_type': 'minutes'
            , 'interval_number': 2
            , 'model_id': model_id.id
            , 'state': 'code'
            , 'code': my_code
            , 'name': f'Request Reminder - Recurring ({self.id})'
            , 'user_id': 1
        }
        my_cron = self.env['ir.cron'].sudo()
        my_cron.create(my_job)
        id1 = my_cron.search([('id', '=', 1)])

    def reminder(self, request_id, message):
        print(f"Reminder: {datetime.datetime.now()}")
        notification_ids = []
        request = self.env['lean.request'].sudo().search([('id', '=', request_id)])
        if request.state in ['review', 'in_progress']:
            notification_ids.append((0, 0, {
                'res_partner_id': request.create_uid.partner_id.id,
                'notification_type': 'inbox'}))
            request.sudo().message_post(
                subject=message,
                body=message
                , message_type='notification'
                , notification_ids=notification_ids
                , subtype="mail.mt_comment"
                , author_id=self.env.user.partner_id.id,
            )

            # web notify
            admin = self.env['res.users'].browse(2)
            request.create_uid.with_user(admin).notify_info(message)

    def delete_reminder(self, type):
        cron_name = f'Request Reminder - {type} ({self.id})'
        cron = self.env['ir.cron'].sudo()
        my_cron = cron.with_context(active_test=False).search([('name', '=', cron_name)])
        if my_cron:
            my_cron.unlink()

    def change_to_under_review(self):
        for s in self:
            s.sudo().state = 'review'
            s.create_reminder_once()
            s.notify('review')

    def change_to_in_progress(self):
        for s in self:
            s.sudo().state = 'in_progress'
            s.create_reminder_recurring()
            s.delete_reminder('One Time')

    def change_to_completed(self):
        for s in self:
            s.sudo().state = 'completed'
            s.sudo().notify('completed')
            s.delete_reminder('Recurring')

    @api.model
    def create(self, vals):
        request_id = super(Request, self).create(vals)
        self.create_tracker(request_id.id)
        return request_id

    def create_tracker(self, request_id):
        model_id = self.env['ir.model'].sudo().search([('name', '=', 'lean.request')])
        my_code = f"model.tracker({request_id})"
        next_call = datetime.datetime.now()
        my_job = {
            'nextcall': next_call
            , 'priority': 1
            , 'numbercall': -1
            , 'interval_type': 'minutes'
            , 'interval_number': 1
            , 'model_id': model_id.id
            , 'state': 'code'
            , 'code': my_code
            , 'name': f'Request Tracker ({request_id})'
            , 'user_id': 1
        }
        my_cron = self.env['ir.cron'].sudo()
        my_cron.create(my_job)
        id1 = my_cron.search([('id', '=', 1)])

    def tracker(self, request_id):
        my_request = self.env['lean.request'].sudo().browse(request_id)
        if my_request.state != 'completed':
            create_date = my_request.create_date
            elapsed_time = (datetime.datetime.now() - create_date).total_seconds() / 60
            print (f'Elapsed time:{elapsed_time}')
            if elapsed_time < 5:
                my_request.tracker_tag = 'on_track'
            elif elapsed_time > 5 and elapsed_time < 15:
                my_request.tracker_tag = 'due_soon'
            elif elapsed_time > 15:
                my_request.tracker_tag = 'over_due'


