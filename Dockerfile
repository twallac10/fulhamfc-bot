FROM python:3.12-slim-trixie

WORKDIR /app

# System dependencies: build tools for Python wheels, Ruby for Jekyll, git for the workflows
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libxml2-dev \
    libxslt1-dev \
    ruby-full \
    build-essential \
    zlib1g-dev \
    git \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Ruby/Jekyll dependencies
COPY Gemfile Gemfile.lock ./
RUN gem install bundler && bundle install

ENV PYTHONPATH=/app

CMD ["bash"]
