# A portable solution: download image from Docker Hub.
# FROM caddy:2.11-alpine

# A less portable solution: download image through a cache proxy provided by the University.
# This solution is necessary to avoid "Too many requests" errors.
# This solution won't work outside the University network.
FROM harbor.pg.innopolis.university/docker-hub-cache/caddy:2.11-alpine

RUN mkdir -p /srv

RUN cat <<'EOF' > /srv/index.html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Learning Management Service</title>
    <style>
      body {
        margin: 0;
        font-family: sans-serif;
        background: #f4f1ea;
        color: #1c1a17;
      }
      main {
        max-width: 720px;
        margin: 10vh auto;
        padding: 2rem;
      }
      a {
        color: #0b57d0;
      }
      .card {
        background: #fffaf0;
        border: 1px solid #d8cfbe;
        border-radius: 16px;
        padding: 1.5rem;
      }
    </style>
  </head>
  <body>
    <main>
      <div class="card">
        <h1>Learning Management Service</h1>
        <p>The API is available through this reverse proxy.</p>
        <p>Open <a href="/docs">/docs</a> for Swagger UI.</p>
      </div>
    </main>
  </body>
</html>
EOF
