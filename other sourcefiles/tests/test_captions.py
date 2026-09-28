from __future__ import annotations
import json, sys, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.captions import _parse_caption

class CaptionParserTests(unittest.TestCase):
    def test_vtt(self):
        c=_parse_caption("WEBVTT\n\n00:00:01.000 --> 00:00:02.500\nHello <b>world</b>!\n","vtt")
        self.assertEqual(c[0]["text"],"Hello world!")
    def test_srv3(self):
        c=_parse_caption('<timedtext><body><p t="1500" d="2500">Hello <s>world</s></p></body></timedtext>',"srv3")
        self.assertEqual(c[0]["text"],"Hello world")
        self.assertAlmostEqual(c[0]["start"],1.5)
        c=_parse_caption('<timedtext><body><p t="0" d="1000">Hello   <s>   world   </s></p></body></timedtext>',"srv3")
        self.assertEqual(c[0]["text"],"Hello world")
    def test_json3(self):
        c=_parse_caption(json.dumps({"events":[{"tStartMs":2000,"dDurationMs":1200,"segs":[{"utf8":"Hello "},{"utf8":"world"}]}]}),"json3")
        self.assertEqual(c[0]["text"],"Hello world")
    def test_ttml(self):
        c=_parse_caption('<tt xmlns="http://www.w3.org/ns/ttml"><body><p begin="00:00:03.000" end="00:00:05.500">Hello <span>world</span></p></body></tt>',"ttml")
        self.assertEqual(c[0]["text"],"Hello world")
        self.assertAlmostEqual(c[0]["end"],5.5)

if __name__=="__main__":
 unittest.main()
