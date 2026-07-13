-- ═══════════════════════════════════════════════════════════════
--  PROJECT KOWALSKI — SQL FUNCTIONS
--  Run AFTER schema.sql, in the Supabase SQL Editor.
--
--  These live in Postgres rather than Python because they need the
--  GIN indexes. Doing this in Python would mean pulling every row
--  over the network and filtering in a for-loop.
-- ═══════════════════════════════════════════════════════════════


-- ───────────────────────────────────────────────────────────────
--  SEARCH
--  Three strategies, best-first:
--    1. full-text   — real word matching, ranked
--    2. trigram     — typo tolerance ("fatma" finds Fatima)
--    3. substring   — the blunt instrument, always works
-- ───────────────────────────────────────────────────────────────
create or replace function search_items(q text, limit_n int default 20)
returns setof items
language sql
stable
as $$
    select *
    from items
    where deleted_at is null
      and (
            search_vector @@ plainto_tsquery('simple', q)
         or content % q
         or content ilike '%' || q || '%'
      )
    order by
        ts_rank(search_vector, plainto_tsquery('simple', q)) desc,
        similarity(content, q) desc,
        created_at desc
    limit limit_n;
$$;


-- ───────────────────────────────────────────────────────────────
--  ENTITY RESOLUTION
--  "fatima" / "Fatima" / "fatma" / "fati" -> one row.
--
--  Order is deliberate: exact name, then exact alias, then fuzzy.
--  The 0.4 similarity floor is a judgement call — high enough to
--  reject nonsense, low enough to forgive a phone keyboard.
-- ───────────────────────────────────────────────────────────────
create or replace function resolve_entity(q text)
returns setof entities
language sql
stable
as $$
    with candidates as (
        -- exact name
        select e.*, 1.0::real as score
        from entities e
        where e.deleted_at is null
          and lower(e.name) = lower(trim(q))

        union all

        -- exact alias
        select e.*, 0.9::real as score
        from entities e
        join entity_aliases a on a.entity_id = e.id
        where e.deleted_at is null
          and lower(a.alias) = lower(trim(q))

        union all

        -- fuzzy name
        select e.*, similarity(e.name, q)::real as score
        from entities e
        where e.deleted_at is null
          and similarity(e.name, q) > 0.4

        union all

        -- fuzzy alias
        select e.*, (similarity(a.alias, q) * 0.85)::real as score
        from entities e
        join entity_aliases a on a.entity_id = e.id
        where e.deleted_at is null
          and similarity(a.alias, q) > 0.4
    )
    select id, name, kind, meta, created_at, updated_at, deleted_at
    from candidates
    order by score desc
    limit 1;
$$;


-- ───────────────────────────────────────────────────────────────
--  SMOKE TESTS
-- ───────────────────────────────────────────────────────────────
-- select * from resolve_entity('jersey');       -- should find Jersey Fiesta
-- select * from resolve_entity('jrsey festa');  -- should ALSO find it
-- select * from search_items('kowalski');
