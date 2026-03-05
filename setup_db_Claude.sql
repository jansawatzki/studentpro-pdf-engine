-- Run this once in Supabase SQL Editor

-- 1. Enable pgvector extension
create extension if not exists vector;

-- 2. Create documents table
create table if not exists documents (
  id bigserial primary key,
  filename text not null,
  page_number int not null,
  content text,
  embedding vector(1024),
  unique(filename, page_number)
);

-- 3. Create similarity search function
create or replace function match_documents(
  query_embedding vector(1024),
  match_count int default 5
)
returns table (
  id bigint,
  filename text,
  page_number int,
  content text,
  similarity float
)
language sql stable
as $$
  select
    id,
    filename,
    page_number,
    content,
    1 - (embedding <=> query_embedding) as similarity
  from documents
  order by embedding <=> query_embedding
  limit match_count;
$$;
