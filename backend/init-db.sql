--
-- PostgreSQL database initialization script
--

-- Create extensions and settings
SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

-- Search path
SELECT pg_catalog.set_config('search_path', '', false);

-- Create sequences
CREATE SEQUENCE public.players_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

CREATE SEQUENCE public.lobbies_lobby_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Create tables
CREATE TABLE public.players (
    id integer NOT NULL DEFAULT nextval('public.players_id_seq'),
    login text NOT NULL,
    password text NOT NULL,
    nickname text,
    rating bigint DEFAULT 0,
    CONSTRAINT players_pkey PRIMARY KEY (id),
    CONSTRAINT players_login_key UNIQUE (login)
);

CREATE TABLE public.lobbies (
    lobby_id bigint NOT NULL DEFAULT nextval('public.lobbies_lobby_id_seq'),
    lobby_name text NOT NULL,
    capacity integer,
    date timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    admin_id integer,
    active boolean,
    CONSTRAINT lobbies_pkey PRIMARY KEY (lobby_id),
    CONSTRAINT lobbies_admin_id_fkey FOREIGN KEY (admin_id) REFERENCES public.players(id)
);

CREATE TABLE public.lobbymembers (
    player_id bigint NOT NULL,
    lobby_id bigint NOT NULL,
    joined_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    place integer,
    points integer,
    change_rating integer,
    CONSTRAINT lobbymembers_pkey PRIMARY KEY (player_id, lobby_id),
    CONSTRAINT lobbymembers_player_id_fkey FOREIGN KEY (player_id) REFERENCES public.players(id) ON DELETE CASCADE,
    CONSTRAINT lobbymembers_lobby_id_fkey FOREIGN KEY (lobby_id) REFERENCES public.lobbies(lobby_id) ON DELETE CASCADE
);

-- Create functions

-- Add a new lobby
CREATE OR REPLACE FUNCTION public.add_lobby(
    name text,
    cap integer,
    id integer
) RETURNS bigint
LANGUAGE plpgsql
AS $$
DECLARE
    new_lobby_id bigint;
BEGIN
    INSERT INTO public.lobbies(lobby_name, capacity, admin_id, active)
    VALUES (name, cap, id, true)
    RETURNING lobby_id INTO new_lobby_id;

    RETURN new_lobby_id;
END;
$$;

-- Add a new user
CREATE OR REPLACE FUNCTION public.add_user(
    p_nickname text,
    p_login text,
    p_password text
) RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO public.players (nickname, login, password)
    VALUES (p_nickname, p_login, p_password);
END;
$$;

-- Add a user to a lobby
CREATE OR REPLACE FUNCTION public.add_user_in_lobby(
    p_id bigint,
    l_id bigint
) RETURNS void
LANGUAGE plpgsql
AS $$
BEGIN
    INSERT INTO public.lobbymembers(player_id, lobby_id, place, points, change_rating)
    VALUES (p_id, l_id, 0, 0, 0);
END;
$$;

-- Authorization function
CREATE OR REPLACE FUNCTION public.authorization(
    log text,
    pass text
) RETURNS TABLE(user_count integer, user_id integer, nickname text, rating bigint)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        CASE WHEN EXISTS (
            SELECT 1 FROM public.players WHERE login = log AND password = pass
        ) THEN 1 ELSE 0 END,
        p.id,
        p.nickname,
        p.rating
    FROM public.players p
    WHERE p.login = log AND p.password = pass;

    IF NOT FOUND THEN
        RETURN QUERY SELECT 0, NULL::integer, NULL::text, NULL::bigint;
    END IF;
END;
$$;

-- Get player info by ID
CREATE OR REPLACE FUNCTION public.get_info_p(target_id integer)
RETURNS TABLE(login text, nickname text, rating bigint)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT p.login, p.nickname, p.rating
    FROM public.players p
    WHERE p.id = target_id;
END;
$$;

-- Get player info by login
CREATE OR REPLACE FUNCTION public.get_info_p(log text)
RETURNS TABLE(id integer, nickname text, rating bigint)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT p.id, p.nickname, p.rating
    FROM public.players p
    WHERE p.login = log;
END;
$$;

