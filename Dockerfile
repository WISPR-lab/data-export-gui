FROM node:22-bookworm-slim

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apt-get update && apt-get install -y --no-install-recommends \
	bash \
	build-essential \
	curl \
	git \
	ca-certificates \
	tar \
	zip \
	&& uv python install 3.12 \
	&& ln -sf "$(uv python find 3.12)" /usr/local/bin/python \
	&& ln -sf "$(uv python find 3.12)" /usr/local/bin/python3 \
	&& ln -sf "$(uv python find 3.12)" /usr/local/bin/python3.12 \
	&& corepack enable \
	&& corepack prepare yarn@1.22.22 --activate \
	&& rm -rf /var/lib/apt/lists/*

ENV UV_PYTHON=3.12
WORKDIR /workspace

COPY pyproject.toml uv.lock ./
COPY UA-Extract-purepy ./UA-Extract-purepy
RUN uv sync --frozen

COPY webapp/package.json webapp/yarn.lock ./webapp/
RUN cd webapp && yarn install

COPY . .

EXPOSE 5001

CMD ["yarn", "--cwd", "webapp", "serve"]
