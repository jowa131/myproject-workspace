# UI And Content Regression Checklist

Use this checklist for browser-facing changes, especially in `yulchive-astro`
and routes published under `yulchive.com`.

## Required For Affected Routes

- Desktop viewport renders without horizontal overflow.
- Mobile viewport around 390px renders without horizontal overflow.
- Main heading count and hierarchy are intentional.
- Images load and keep expected aspect ratio.
- Captions and adjacent body text are not confused.
- Interactive controls have visible focus and usable labels.
- Console has no relevant runtime errors.

## Content Publishing Checks

- Detail route returns HTTP 200 locally or publicly as appropriate.
- Home/listing page includes or excludes the item as intended.
- Tag/category page state is correct.
- RSS and sitemap behavior is correct when the content should be public.
- 404 behavior is correct for private or temporary routes.
- Ads, Giscus, previous/next links, and lazy images still render when present.

## Report Format

```text
Route:
Viewport:
Checks:
Result:
Evidence:
Notes:
```

