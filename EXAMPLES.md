# EXAMPLES — design/03-tinyurl

## E1 — first shorten

```http
POST /shorten
{ "long_url": "https://en.wikipedia.org/wiki/URL_shortening" }
```

→ `201`

```json
{ "long_url": "https://en.wikipedia.org/wiki/URL_shortening",
  "short_code": "aB3xY7",
  "short_url": "https://your-host/aB3xY7" }
```

## E2 — same long URL again (idempotent)

```http
POST /shorten
{ "long_url": "https://en.wikipedia.org/wiki/URL_shortening" }
```

→ `200` with the **same** `short_code: "aB3xY7"` as E1. Repeat 5 times — same code each time.

## E3 — custom alias accepted

```http
POST /shorten
{ "long_url": "https://my-awesome-blog.example.com/post-1",
  "alias": "post1" }
```

→ `201 { "short_code": "post1", ... }`

## E4 — alias conflict

```http
POST /shorten
{ "long_url": "https://different.example.com/whatever",
  "alias": "post1" }   # already used in E3 for a different URL
```

→ `409 { "error": "alias 'post1' is already taken" }`

## E5 — alias for same URL is idempotent

```http
POST /shorten
{ "long_url": "https://my-awesome-blog.example.com/post-1",
  "alias": "post1" }   # same URL, same alias as E3
```

→ `200 { "short_code": "post1", ... }`

## E6 — round-trip redirect

```http
GET /aB3xY7
```

→ `302 Location: https://en.wikipedia.org/wiki/URL_shortening`

## E7 — non-existent code

```http
GET /zzzzz9
```

→ `404 { "error": "no such short code" }`

## E8 — programmatic expand

```http
GET /api/expand/aB3xY7
```

→ `200`

```json
{ "short_code": "aB3xY7",
  "long_url": "https://en.wikipedia.org/wiki/URL_shortening",
  "created_at": "2026-04-29T08:30:00Z" }
```

## E9 — stats (after 5 distinct shortens + 12 redirects)

```http
GET /stats
```

→ `200 { "total_links": 5, "total_redirects": 12 }`

## E10 — invalid URL

```http
POST /shorten
{ "long_url": "not-a-url" }
```

→ `400 { "error": "long_url must be a valid http(s) URL" }`
