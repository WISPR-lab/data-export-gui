FROM nikolaik/python-nodejs:python3.12-nodejs18-alpine

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

RUN apk add --no-cache bash git build-base

WORKDIR /workspace

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY package.json yarn.lock ./
COPY webapp/package.json webapp/yarn.lock ./webapp/
RUN cd webapp && yarn install

COPY . .

EXPOSE 5001

CMD ["yarn", "--cwd", "webapp", "serve"]
