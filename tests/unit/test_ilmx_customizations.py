"""
Tests for the ilmX customisations of the Drag and Drop v2 XBlock.
"""
import unittest
from importlib import resources
from importlib.metadata import entry_points

import mock

from drag_and_drop_v2 import DragAndDropBlock

from ..utils import TestCaseMixin, make_block

SUCCESS_URL = 'https://cdn.example.org/sounds/correct.mp3'
FAILURE_URL = 'https://cdn.example.org/sounds/wrong.mp3'


def _asset(path):
    return resources.files('drag_and_drop_v2').joinpath(path).read_text(encoding='utf-8')


class IlmxSoundSettingsTests(TestCaseMixin, unittest.TestCase):
    """Feedback sounds are configured through XBLOCK_SETTINGS['drag-and-drop-v2']."""

    def setUp(self):
        self.block = make_block()
        self.patch_workbench()

    def _patch_settings(self, value):
        patcher = mock.patch.object(DragAndDropBlock, 'get_xblock_settings', return_value=value)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_sounds_disabled_by_default(self):
        self._patch_settings({})
        self.assertEqual(self.block.ilmx_sound_urls(), {'success_url': None, 'failure_url': None})

    def test_sounds_disabled_when_settings_missing(self):
        self._patch_settings(None)
        self.assertEqual(self.block.ilmx_sound_urls(), {'success_url': None, 'failure_url': None})

    def test_sounds_configured(self):
        self._patch_settings({'ILMX_SUCCESS_SOUND_URL': SUCCESS_URL, 'ILMX_FAILURE_SOUND_URL': FAILURE_URL})
        self.assertEqual(
            self.block.ilmx_sound_urls(), {'success_url': SUCCESS_URL, 'failure_url': FAILURE_URL}
        )

    def test_student_view_passes_sounds_to_js_but_not_to_api(self):
        self._patch_settings({'ILMX_SUCCESS_SOUND_URL': SUCCESS_URL, 'ILMX_FAILURE_SOUND_URL': FAILURE_URL})
        fragment = self.block.student_view({})
        self.assertEqual(
            fragment.json_init_args['ilmx_sounds'], {'success_url': SUCCESS_URL, 'failure_url': FAILURE_URL}
        )
        # The mobile/Course Blocks API payload stays identical to upstream.
        self.assertNotIn('ilmx_sounds', self.block.student_view_data())


class IlmxCompatibilityTests(unittest.TestCase):
    """Block type and field names must match Juniper so existing content keeps working."""

    def test_entry_point_unchanged(self):
        eps = {ep.name: ep.value for ep in entry_points(group='xblock.v1')}
        self.assertEqual(eps.get('drag-and-drop-v2'), 'drag_and_drop_v2:DragAndDropBlock')

    def test_juniper_fields_present(self):
        juniper_fields = [
            'display_name', 'mode', 'max_attempts', 'show_title', 'question_text', 'show_question_header',
            'weight', 'item_background_color', 'item_text_color', 'max_items_per_zone', 'data',
            'item_state', 'attempts', 'completed', 'grade', 'raw_earned', 'raw_possible',
        ]
        for name in juniper_fields:
            self.assertIn(name, DragAndDropBlock.fields, name)


class IlmxAssetTests(unittest.TestCase):
    """Static asset checks for the ilmX UI changes."""

    def test_js_outlines_zones_while_dragging(self):
        js = _asset('public/js/drag_and_drop.js')
        self.assertIn("$('.zone', $element).addClass('drop-zones-outline')", js)
        self.assertIn("$('.zone', $element).removeClass('drop-zones-outline')", js)

    def test_js_sounds_are_configurable_not_hardcoded(self):
        js = _asset('public/js/drag_and_drop.js')
        self.assertIn('configuration.ilmx_sounds', js)
        self.assertIn('playSound(success_audio)', js)
        self.assertIn('playSound(failure_audio)', js)
        self.assertNotIn('amazonaws.com', js)

    def test_css_ilmx_styles(self):
        css = _asset('public/css/drag_and_drop.css')
        self.assertIn('.xblock--drag-and-drop .zone.drop-zones-outline', css)
        self.assertIn('.xblock--drag-and-drop .dragged-items .option', css)
        self.assertIn('#BFEFE0', css)  # correct-feedback popup colour
        self.assertIn('#FFD7BB', css)  # incorrect-feedback popup colour
