import tempfile

import pytest

from gesso.main import post_process_fields, render_markdown


class TestPostProcessFields:
    """Test post_process_fields function with various inputs."""

    def test_normal_case_all_fields(self):
        """Test normal case with all fields populated."""
        input_data = {
            "title": "Wounded Eurydice",
            "artist": "Jean Baptiste Camille Corot",
            "year": 1868,
            "style": "Realism",
            "medium": "Oil on Canvas",
            "museum": "Art Institute of Chicago",
            "image_url": "https://upload.wikimedia.org/wikipedia/commons/example.jpg",
            "description": "A beautiful painting of a wounded figure.",
        }

        result = post_process_fields(input_data)

        assert result["title"] == "Wounded Eurydice"
        assert result["artist"] == "[[Jean Baptiste Camille Corot]]"
        assert result["year"] == 1868
        assert result["style"] == ["[[Realism]]"]
        assert result["medium"] == ["[[Oil on Canvas]]"]
        assert result["museum"] == ["[[Art Institute of Chicago]]"]
        assert (
            result["image"]
            == "https://upload.wikimedia.org/wikipedia/commons/example.jpg"
        )
        assert result["description"] == "A beautiful painting of a wounded figure."
        assert result["tags"] == ["paintings"]

    def test_comma_separated_style_and_medium(self):
        """Test comma-separated values for style, medium, museum."""
        input_data = {
            "title": "Test Painting",
            "artist": "Test Artist",
            "year": 1900,
            "style": "Realism, Impressionism, Symbolism",
            "medium": "Oil on Canvas, Watercolor",
            "museum": "Louvre, Metropolitan Museum",
            "image_url": "https://example.com/image.jpg",
            "description": "Test description",
        }

        result = post_process_fields(input_data)

        assert result["style"] == ["[[Realism]]", "[[Impressionism]]", "[[Symbolism]]"]
        assert result["medium"] == ["[[Oil on Canvas]]", "[[Watercolor]]"]
        assert result["museum"] == ["[[Louvre]]", "[[Metropolitan Museum]]"]

    def test_empty_fields(self):
        """Test with empty/missing fields."""
        input_data = {
            "title": "Untitled",
            "artist": "Unknown Artist",
            "year": "",
            "style": "",
            "medium": "",
            "museum": "",
            "image_url": "",
            "description": "",
        }

        result = post_process_fields(input_data)

        assert result["title"] == "Untitled"
        assert result["artist"] == "[[Unknown Artist]]"
        assert result["year"] == ""
        assert result["style"] == []
        assert result["medium"] == []
        assert result["museum"] == []
        assert result["image"] == ""
        assert result["description"] == ""
        assert result["tags"] == ["paintings"]

    def test_unknown_string_values(self):
        """Test that 'Unknown' string values are treated as empty."""
        input_data = {
            "title": "Mystery Painting",
            "artist": "Unknown",
            "year": "Unknown",
            "style": "Unknown",
            "medium": "Unknown",
            "museum": "Unknown",
            "image_url": "Unknown",
            "description": "Unknown",
        }

        result = post_process_fields(input_data)

        assert result["title"] == "Mystery Painting"
        assert result["artist"] == "[[Unknown]]"
        assert result["year"] == ""
        assert result["style"] == []
        assert result["medium"] == []
        assert result["museum"] == []
        assert result["image"] == ""
        assert result["description"] == "Unknown"

    def test_missing_fields_defaults(self):
        """Test that missing fields use safe defaults."""
        input_data = {"title": "Minimal Data"}

        result = post_process_fields(input_data)

        assert result["title"] == "Minimal Data"
        assert result["artist"] == ""
        assert result["year"] == ""
        assert result["style"] == []
        assert result["medium"] == []
        assert result["museum"] == []
        assert result["image"] == ""
        assert result["description"] == ""
        assert result["tags"] == ["paintings"]

    def test_year_as_integer(self):
        """Test that year can be an integer."""
        input_data = {
            "title": "Old Master",
            "artist": "Renaissance Artist",
            "year": 1450,
            "style": "Renaissance",
            "medium": "Tempera on Panel",
            "museum": "Uffizi Gallery",
            "image_url": "https://example.com/image.jpg",
            "description": "A Renaissance work",
        }

        result = post_process_fields(input_data)

        assert result["year"] == 1450
        assert isinstance(result["year"], int)

    def test_whitespace_handling_in_lists(self):
        """Test that whitespace is properly trimmed in comma-separated values."""
        input_data = {
            "title": "Whitespace Test",
            "artist": "Test Artist",
            "year": 1900,
            "style": "  Realism  ,  Impressionism  ,  Symbolism  ",
            "medium": "  Oil on Canvas  ,  Watercolor  ",
            "museum": "  Louvre  ,  Museum  ",
            "image_url": "https://example.com/image.jpg",
            "description": "Test",
        }

        result = post_process_fields(input_data)

        assert result["style"] == ["[[Realism]]", "[[Impressionism]]", "[[Symbolism]]"]
        assert result["medium"] == ["[[Oil on Canvas]]", "[[Watercolor]]"]
        assert result["museum"] == ["[[Louvre]]", "[[Museum]]"]


class TestRenderMarkdown:
    """Test render_markdown function with various inputs."""

    @pytest.fixture
    def template_file(self):
        """Create a temporary template file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("""---
created: {{date}}
category: "[[Painting]]"
title: "{{title}}"
artist: 
year: 
style:
medium: 
museum:
image: 
rating: 
seen:
tags:
  - paintings
---

# {{title}}

![{{title}}]({{image}})

## Personal Reflection
""")
            return f.name

    def test_normal_case_full_data(self, template_file):
        """Test rendering with all fields populated."""
        painting_data = {
            "title": "Wounded Eurydice",
            "artist": "[[Jean Baptiste Camille Corot]]",
            "year": 1868,
            "style": ["[[Realism]]"],
            "medium": ["[[Oil on Canvas]]"],
            "museum": ["[[Art Institute of Chicago]]"],
            "image": "https://upload.wikimedia.org/wikipedia/commons/example.jpg",
            "description": "A wounded figure in a mythological scene.",
            "tags": ["paintings"],
        }

        result = render_markdown(template_file, painting_data, "2025-12-24")

        assert "created: 2025-12-24" in result
        assert 'title: "Wounded Eurydice"' in result
        assert 'artist: "[[Jean Baptiste Camille Corot]]"' in result
        assert "year: 1868" in result
        assert '  - "[[Realism]]"' in result
        assert '  - "[[Oil on Canvas]]"' in result
        assert '  - "[[Art Institute of Chicago]]"' in result
        assert (
            "image: https://upload.wikimedia.org/wikipedia/commons/example.jpg"
            in result
        )
        assert "# Wounded Eurydice" in result
        assert (
            "![Wounded Eurydice](https://upload.wikimedia.org/wikipedia/commons/example.jpg)"
            in result
        )

    def test_multiple_styles_and_mediums(self, template_file):
        """Test rendering with multiple comma-separated values."""
        painting_data = {
            "title": "Complex Work",
            "artist": "[[Test Artist]]",
            "year": 1950,
            "style": ["[[Modernism]]", "[[Cubism]]", "[[Surrealism]]"],
            "medium": ["[[Oil on Canvas]]", "[[Mixed Media]]"],
            "museum": ["[[MoMA]]", "[[Guggenheim]]"],
            "image": "https://example.com/image.jpg",
            "description": "A complex modern work.",
            "tags": ["paintings"],
        }

        result = render_markdown(template_file, painting_data, "2025-12-24")

        assert '  - "[[Modernism]]"' in result
        assert '  - "[[Cubism]]"' in result
        assert '  - "[[Surrealism]]"' in result
        assert '  - "[[Oil on Canvas]]"' in result
        assert '  - "[[Mixed Media]]"' in result
        assert '  - "[[MoMA]]"' in result
        assert '  - "[[Guggenheim]]"' in result

    def test_empty_fields(self, template_file):
        """Test rendering with empty/missing fields."""
        painting_data = {
            "title": "Untitled Work",
            "artist": "",
            "year": "",
            "style": [],
            "medium": [],
            "museum": [],
            "image": "",
            "description": "",
            "tags": ["paintings"],
        }

        result = render_markdown(template_file, painting_data, "2025-12-24")

        assert 'title: "Untitled Work"' in result
        assert "artist: " in result  # Should be empty
        assert "year: " in result  # Should be empty
        assert "style:" in result  # Should have no list items
        assert "medium:" in result  # Should have no list items
        assert "museum:" in result  # Should have no list items
        assert "image: " in result  # Should be empty

    def test_date_field_replaced(self, template_file):
        """Test that date field is correctly replaced."""
        painting_data = {
            "title": "Test",
            "artist": "[[Artist]]",
            "year": 2000,
            "style": [],
            "medium": [],
            "museum": [],
            "image": "https://example.com/image.jpg",
            "description": "Test",
            "tags": ["paintings"],
        }

        result = render_markdown(template_file, painting_data, "2025-12-25")

        assert "created: 2025-12-25" in result
        assert "created: {{date}}" not in result

    def test_title_in_heading_and_image_alt(self, template_file):
        """Test that title appears in heading and image alt text."""
        painting_data = {
            "title": "The Starry Night",
            "artist": "[[Vincent van Gogh]]",
            "year": 1889,
            "style": ["[[Post-Impressionism]]"],
            "medium": ["[[Oil on Canvas]]"],
            "museum": ["[[MoMA]]"],
            "image": "https://example.com/starry-night.jpg",
            "description": "A swirling night sky.",
            "tags": ["paintings"],
        }

        result = render_markdown(template_file, painting_data, "2025-12-24")

        assert "# The Starry Night" in result
        assert "![The Starry Night](https://example.com/starry-night.jpg)" in result

    def test_special_characters_in_title(self, template_file):
        """Test handling of special characters in title."""
        painting_data = {
            "title": "Woman's Portrait: A Study",
            "artist": "[[Test Artist]]",
            "year": 1900,
            "style": ["[[Realism]]"],
            "medium": ["[[Oil on Canvas]]"],
            "museum": ["[[Museum]]"],
            "image": "https://example.com/image.jpg",
            "description": "A portrait study.",
            "tags": ["paintings"],
        }

        result = render_markdown(template_file, painting_data, "2025-12-24")

        assert 'title: "Woman\'s Portrait: A Study"' in result
        assert "# Woman's Portrait: A Study" in result

    def test_wikilinks_are_quoted_in_yaml(self, template_file):
        """Test that wikilinks are quoted in YAML list items."""
        painting_data = {
            "title": "Test",
            "artist": "[[Test Artist]]",
            "year": 1900,
            "style": ["[[Realism]]"],
            "medium": ["[[Oil on Canvas]]"],
            "museum": ["[[Louvre]]"],
            "image": "https://example.com/image.jpg",
            "description": "Test",
            "tags": ["paintings"],
        }

        result = render_markdown(template_file, painting_data, "2025-12-24")

        # Wikilinks in YAML lists should be quoted
        assert '  - "[[Realism]]"' in result
        assert '  - "[[Oil on Canvas]]"' in result
        assert '  - "[[Louvre]]"' in result

    def test_tags_not_duplicated(self, template_file):
        """Test that tags appear only once in output."""
        painting_data = {
            "title": "Test",
            "artist": "[[Artist]]",
            "year": 1900,
            "style": [],
            "medium": [],
            "museum": [],
            "image": "https://example.com/image.jpg",
            "description": "Test",
            "tags": ["paintings"],
        }

        result = render_markdown(template_file, painting_data, "2025-12-24")

        # Count occurrences of "paintings" tag in YAML section (before ---)
        yaml_section = result.split("---")[
            1
        ]  # Get content between first and second ---
        paintings_count = yaml_section.count("paintings")

        # Should appear exactly once
        assert paintings_count == 1, (
            f"'paintings' tag appears {paintings_count} times, expected 1"
        )
