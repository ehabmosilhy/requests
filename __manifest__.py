# -*- coding: utf-8 -*-
{
    'name': "Requests Module",
    'summary': "Request Tracking Module",
    'description': """The services module enables the employees to submit their requests to the service’s responsible and
track its progress.""",
    'author': "Ehab Mosilhy",
    'website': "",
    'category': '',
    'version': '1.0',
    'depends': ['base', 'mail'],
    'data': [
        'security/groups.xml'
        , 'security/ir.model.access.csv'
        , 'security/record_rules.xml'
        , 'views/request.xml'
        , 'views/main.xml'
    ],
    "installable": True,
    "auto_install": False,
}
