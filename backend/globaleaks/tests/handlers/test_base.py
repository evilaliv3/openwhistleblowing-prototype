# -*- coding: utf-8 -*-
import json

from twisted.internet.defer import inlineCallbacks
from twisted.trial import unittest

from globaleaks.handlers import base
from globaleaks.rest.errors import InvalidInputFormat
from globaleaks.settings import GLSettings
from globaleaks.tests import helpers


class MockHandler(base.BaseHandler):
    def __init__(self):
        pass


class TestValidate(unittest.TestCase):
    _handler = base.BaseHandler
    def test_validate_jmessage_valid(self):
        dummy_message = {'spam': 'ham', 'firstd': {3: 4}, 'fields': "CIAOCIAO", 'nest': [{1: 2, 3: 4}]}
        dummy_message_template = {'spam': str, 'firstd': dict, 'fields': '\w+', 'nest': [dict]}

        handler = MockHandler()
        self.assertTrue(handler.validate_jmessage(dummy_message, dummy_message_template))

        dummy_message = {'key': [{'code': 'it', 'name': 'Italiano'}, {'code': 'en', 'name': 'English'}]}
        dummy_message_template = {'key': list}
        self.assertTrue(handler.validate_jmessage(dummy_message, dummy_message_template))

    def test_validate_jmessage_invalid(self):
        dummy_message = {'spam': 'ham', 'fields': "CIAOCIAO", 'nest': {1: 3, 4: 5}}
        dummy_message_template = {'spam': str, 'fields': '\d+', 'nest': int}

        handler = MockHandler()

        self.assertRaises(InvalidInputFormat,
                          handler.validate_jmessage, dummy_message, dummy_message_template)

    def test_validate_message_valid(self):
        dummy_json = json.dumps({'spam': 'ham'})
        dummy_message_template = {'spam': unicode}

        handler = MockHandler()
        self.assertEqual(json.loads(dummy_json), handler.validate_message(dummy_json, dummy_message_template))

    def test_validate_message_invalid(self):
        dummy_json = json.dumps({'spam': 'ham'})
        dummy_message_template = {'spam': dict}

        handler = MockHandler()

        self.assertRaises(InvalidInputFormat,
                          handler.validate_message, dummy_json, dummy_message_template)

    def test_int_accepted_as_unicode(self):
        """
        Due the fact that angular.js convert int in u'123' unicode number, when a
        field is declared 'int', need to be accepted also if JSON contain an unicode,
        and is cast as int(u'123') when acquired in the Model.
        """
        dummy_int_json = json.dumps({'intvalue': u'123'})
        dummy_int_template = {'intvalue': int}

        handler = MockHandler()
        self.assertEqual(json.loads(dummy_int_json), handler.validate_message(dummy_int_json, dummy_int_template))


    def test_validate_type_valid(self):
        handler = MockHandler()

        self.assertTrue(handler.validate_type('foca', str))
        self.assertTrue(handler.validate_type(True, bool))
        self.assertTrue(handler.validate_type(4, int))
        self.assertTrue(handler.validate_type(u'foca', unicode))
        self.assertTrue(handler.validate_type(['foca', 'fessa'], list))
        self.assertTrue(handler.validate_type({'foca': 1}, dict))

    def test_validate_type_invalid(self):
        handler = MockHandler()

        self.assertFalse(handler.validate_type(1, str))
        self.assertFalse(handler.validate_type(1, unicode))
        self.assertFalse(handler.validate_type(False, unicode))
        self.assertFalse(handler.validate_type({}, list))
        self.assertFalse(handler.validate_type(True, dict))

    def test_validate_python_type_valid(self):
        handler = MockHandler()

        self.assertTrue(handler.validate_python_type('foca', str))
        self.assertTrue(handler.validate_python_type(True, bool))
        self.assertTrue(handler.validate_python_type(4, int))
        self.assertTrue(handler.validate_python_type(u'foca', unicode))
        self.assertTrue(handler.validate_python_type(None, dict))

    def test_validate_regexp_valid(self):
        handler = MockHandler()
        self.assertTrue(handler.validate_regexp('Foca', '\w+'))
        self.assertFalse(handler.validate_regexp('Foca', '\d+'))


    def test_validate_host(self):
        self.assertFalse(base.validate_host(""))
        self.assertTrue(base.validate_host("127.0.0.1"))
        self.assertTrue(base.validate_host("thirteenchars123.onion"))
        self.assertTrue(base.validate_host("thirteenchars123.onion:31337"))
        self.assertFalse(base.validate_host("invalid.onion"))
        self.assertFalse(base.validate_host("invalid.onion:12345"))  # gabanbus i miss you!


class TestTimingStats(helpers.TestHandler):
    _handler = base.TimingStatsHandler

    @inlineCallbacks
    def setUp(self):
        yield super(TestTimingStats, self).setUp()
        base.TimingStatsHandler.TimingsTracker = []

    @inlineCallbacks
    def test_get_feature_disabled(self):
        GLSettings.log_timing_stats = False

        base.TimingStatsHandler.log_measured_timing("JOB", "Session Management", 1443252274.44, 0)
        base.TimingStatsHandler.log_measured_timing("GET", "/styles/main.css", 1443252277.68, 0)

        handler = self.request()

        yield handler.get()

        splits = self.responses[0].split("\n")

        self.assertEqual(len(splits), 2)

        self.assertEqual(splits[0], "category,method,uri,start_time,run_time")
        self.assertEqual(splits[1], "")

    @inlineCallbacks
    def test_get_feature_enabled(self):
        GLSettings.log_timing_stats = True

        base.TimingStatsHandler.log_measured_timing("JOB", "Session Management", 1443252274.44, 0)
        base.TimingStatsHandler.log_measured_timing("GET", "/styles/main.css", 1443252277.68, 0)
        base.TimingStatsHandler.log_measured_timing("JOB", "Delivery", 1443252279.0, 0)
        base.TimingStatsHandler.log_measured_timing("POST", "/token", 1443252280.0, 0)
        base.TimingStatsHandler.log_measured_timing("PUT", "/submission/XXA82cSXFHTOoVroWlOGqg2VF8XtJQ57QIYM09YanY", 1443252281.0, 0)
        base.TimingStatsHandler.log_measured_timing("POST", "/wbtip/comments", 1443252282.0, 0)
        handler = self.request()

        yield handler.get()

        splits = self.responses[0].split("\n")

        self.assertEqual(len(splits), 8)

        self.assertEqual(splits[0], "category,method,uri,start_time,run_time")
        self.assertEqual(splits[1], "uncategorized,JOB,Session Management,1443252274.44,0")
        self.assertEqual(splits[2], "uncategorized,GET,/styles/main.css,1443252277.68,0")
        self.assertEqual(splits[3], "delivery,JOB,Delivery,1443252279.0,0")
        self.assertEqual(splits[4], "token,POST,/token,1443252280.0,0")
        self.assertEqual(splits[5], "submission,PUT,/submission/XXA82cSXFHTOoVroWlOGqg2VF8XtJQ57QIYM09YanY,1443252281.0,0")
        self.assertEqual(splits[6], "comment,POST,/wbtip/comments,1443252282.0,0")
        self.assertEqual(splits[7], "")

    @inlineCallbacks
    def test_get_feature_enabled_discard_timingstatss_handler_logging(self):
        GLSettings.log_timing_stats = True

        base.TimingStatsHandler.log_measured_timing("GET", "/s/timings", 1443252274.44, 0)

        handler = self.request()

        yield handler.get()

        splits = self.responses[0].split("\n")

        self.assertEqual(len(splits), 2)

        self.assertEqual(splits[0], "category,method,uri,start_time,run_time")
        self.assertEqual(splits[1], "")
