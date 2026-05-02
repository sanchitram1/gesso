# Enrichment proposal: `example-retrieve.md`

## Source
- **Note:** `/Users/sanch/workspace/gesso/data/example-retrieve.md`
- **Template:** `/Users/sanch/Obsidian/collections/Templates/Painting Template.md`
- **Cache:** `.cache`
- **Attachments (reference):** `/Users/sanch/Obsidian/collections/Attachments`

## Summary
- **Queryable template fields:** year, style, medium, museum, image
- **API call:** yes (kimi / kimi-k2.6)
- **Fields updated in proposal:** (none)
- **Still empty / unresolved:** image, medium, museum, style

## Fields changed
- _(no factual fields changed)_

## Unresolved / left unchanged
These queryable fields were missing before and remain empty or unknown after fetch/cache:
- `image`
- `medium`
- `museum`
- `style`

## LLM request
- **Provider:** `kimi`
- **Model:** `kimi-k2.6`
- **Template fields queried:** style, medium, museum, image

```json
{
  "model": "kimi-k2.6",
  "messages": [
    {
      "role": "user",
      "content": "Return a JSON object with the following fields for this painting:\n- title: \"Retrieve\"\n- artist: \"Himanshu Jamad\"\n- style: (single string, e.g., \"Realism\" or comma-separated if multiple)\n- medium: (single string, e.g., \"Oil on Canvas\")\n- museum: (single string, e.g., \"Art Institute of Chicago\")\n- image_url: (Wikimedia Commons URL preferred, or empty string)\n\nReturn ONLY valid JSON, no other text."
    }
  ]
}
```


## LLM response (raw)
````text
```json
{
  "title": "Retrieve",
  "artist": "Himanshu Jamad",
  "style": "",
  "medium": "",
  "museum": "",
  "image_url": ""
}
```
````


## Image candidate
- **URL / value:** _(none)_
- **Source:** kimi / kimi-k2.6 — responses are merged into the JSON cache bucket

## Current frontmatter
```yaml
created: 2026-01-06
category: '[[Painting]]'
title: Retrieve
artist: '[[Himanshu Jamad]]'
year: 2016
style: null
medium: null
museum: null
image: null
rating: null
seen: null
tags:
- paintings
```

## Proposed frontmatter
```yaml
created: 2026-01-06
category: '[[Painting]]'
title: Retrieve
artist: '[[Himanshu Jamad]]'
year: 2016
style: null
medium: null
museum: null
image: null
rating: null
seen: null
tags:
- paintings
```
