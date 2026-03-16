"""
Unit tests for ImageService — font listing, Hebrew BiDi rendering, image generation.
No network required.
"""
import os
import pytest
from PIL import Image as PILImage

from services.image_service import ImageService
from models.schemas import TextConfig


@pytest.fixture(scope="module", params=["tests/fonts_tmp"])
def svc(tmp_path_factory):
    fonts_dir = str(tmp_path_factory.mktemp("fonts"))
    return ImageService(fonts_dir)


@pytest.fixture
def base_config():
    return TextConfig(
        font_name="Arial",
        font_size=48,
        font_color="#FFFFFF",
        x_percent=0.5,
        y_percent=0.5,
        align="center",
        stroke_width=0,
        stroke_color="#000000",
    )


# ── Font listing ──────────────────────────────────────────────────────────────

class TestFontListing:
    def test_returns_list(self, svc):
        fonts = svc.get_available_fonts()
        assert isinstance(fonts, list)
        assert len(fonts) > 0

    def test_every_font_has_name_path_source(self, svc):
        for f in svc.get_available_fonts():
            assert "name"   in f
            assert "path"   in f
            assert "source" in f

    def test_source_values_valid(self, svc):
        allowed = {"custom", "system"}
        for f in svc.get_available_fonts():
            assert f["source"] in allowed, f"Unexpected source: {f['source']}"

    def test_no_duplicate_names(self, svc):
        names = [f["name"] for f in svc.get_available_fonts()]
        assert len(names) == len(set(names)), "Duplicate font names found"


# ── Image generation ──────────────────────────────────────────────────────────

class TestImageGeneration:
    def _make_template(self, tmp_path, width=400, height=200):
        img = PILImage.new("RGB", (width, height), color=(30, 50, 100))
        path = tmp_path / "template.png"
        img.save(str(path))
        return str(path)

    def test_generate_no_exception(self, svc, tmp_path, base_config):
        template = self._make_template(tmp_path)
        out = str(tmp_path / "out.png")
        svc.generate_image(template, "ישראל", out, base_config)
        assert os.path.exists(out)

    def test_output_is_valid_image(self, svc, tmp_path, base_config):
        template = self._make_template(tmp_path)
        out = str(tmp_path / "out.png")
        svc.generate_image(template, "שרה", out, base_config)
        img = PILImage.open(out)
        assert img.size == (400, 200)

    def test_output_dimensions_match_template(self, svc, tmp_path, base_config):
        template = self._make_template(tmp_path, 800, 600)
        out = str(tmp_path / "big.png")
        svc.generate_image(template, "דוד", out, base_config)
        w, h = PILImage.open(out).size
        assert w == 800
        assert h == 600

    def test_with_stroke(self, svc, tmp_path):
        template = self._make_template(tmp_path)
        cfg = TextConfig(
            font_name="Arial",
            font_size=60,
            font_color="#FF0000",
            x_percent=0.5,
            y_percent=0.5,
            align="center",
            stroke_width=3,
            stroke_color="#000000",
        )
        out = str(tmp_path / "stroked.png")
        svc.generate_image(template, "בדיקה", out, cfg)
        assert os.path.exists(out)

    def test_missing_template_raises(self, svc, tmp_path, base_config):
        with pytest.raises(Exception):
            svc.generate_image("/no/such/file.png", "שם", str(tmp_path / "out.png"), base_config)

    def test_english_name(self, svc, tmp_path, base_config):
        template = self._make_template(tmp_path)
        out = str(tmp_path / "en.png")
        svc.generate_image(template, "John Doe", out, base_config)
        assert os.path.exists(out)

    def test_mixed_hebrew_english_name(self, svc, tmp_path, base_config):
        template = self._make_template(tmp_path)
        out = str(tmp_path / "mixed.png")
        svc.generate_image(template, "ישראל Smith", out, base_config)
        assert os.path.exists(out)

    def test_very_long_name(self, svc, tmp_path, base_config):
        template = self._make_template(tmp_path)
        name = "שם ארוך מאוד עם הרבה מילים שלא אמורות לגרום לקריסה"
        out = str(tmp_path / "long.png")
        svc.generate_image(template, name, out, base_config)
        assert os.path.exists(out)

    def test_name_with_special_chars(self, svc, tmp_path, base_config):
        template = self._make_template(tmp_path)
        out = str(tmp_path / "special.png")
        svc.generate_image(template, "O'Brien", out, base_config)
        assert os.path.exists(out)

    @pytest.mark.parametrize("align", ["left", "center", "right"])
    def test_all_alignments(self, svc, tmp_path, align):
        template = self._make_template(tmp_path)
        cfg = TextConfig(
            font_name="Arial",
            font_size=40,
            font_color="#FFFFFF",
            x_percent=0.5,
            y_percent=0.5,
            align=align,
            stroke_width=0,
            stroke_color="#000000",
        )
        out = str(tmp_path / f"{align}.png")
        svc.generate_image(template, "טקסט", out, cfg)
        assert os.path.exists(out), f"File not created for align={align}"


# ── Hebrew BiDi helper ────────────────────────────────────────────────────────

class TestHebrewBidi:
    def test_prepare_hebrew_returns_string(self, svc):
        result = svc._prepare_hebrew("שלום")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_prepare_english_returns_unchanged(self, svc):
        result = svc._prepare_hebrew("Hello")
        assert result == "Hello"

    def test_prepare_empty_string(self, svc):
        result = svc._prepare_hebrew("")
        assert isinstance(result, str)

    def test_prepare_mixed(self, svc):
        result = svc._prepare_hebrew("Hello שלום")
        assert isinstance(result, str)
        assert len(result) > 0
