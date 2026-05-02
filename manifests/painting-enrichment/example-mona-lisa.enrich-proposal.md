# Enrichment proposal: `example-mona-lisa.md`

## Source
- **Note:** `/Users/sanch/workspace/gesso/data/example-mona-lisa.md`
- **Template:** `/Users/sanch/Obsidian/collections/Templates/Painting Template.md`
- **Cache:** `.cache`
- **Attachments (reference):** `/Users/sanch/Obsidian/collections/Attachments`

## Summary
- **Queryable template fields:** year, style, medium, museum, image
- **API call:** no (cache / no missing fields) (kimi / kimi-k2.6)
- **Fields updated in proposal:** image, medium, museum, style, year
- **Still empty / unresolved:** (none)

## Fields changed
- `image`
- `medium`
- `museum`
- `style`
- `year`

## Unresolved / left unchanged
These queryable fields were missing before and remain empty or unknown after fetch/cache:
- _(none)_

## Image candidate
- **URL / value:** https://upload.wikimedia.org/wikipedia/commons/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg
- **Source:** Resolved entirely from `.cache/` on this session (no live query)

## Current frontmatter
```yaml
created: 2026-05-01
category: '[[Painting]]'
title: Mona Lisa
artist: '[[Leonardo da Vinci]]'
year: null
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
created: 2026-05-01
category: '[[Painting]]'
title: Mona Lisa
artist: '[[Leonardo da Vinci]]'
year: 1503
style:
- '[[High Renaissance]]'
medium:
- '[[Oil on poplar panel]]'
museum:
- '[[Louvre Museum]]'
image: https://upload.wikimedia.org/wikipedia/commons/e/ec/Mona_Lisa%2C_by_Leonardo_da_Vinci%2C_from_C2RMF_retouched.jpg
rating: null
seen: null
tags:
- paintings
```
