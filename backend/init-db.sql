--
-- PostgreSQL database dump
--

-- Dumped from database version 17.2
-- Dumped by pg_dump version 17.2

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: add_lobby(text, integer, integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.add_lobby(name text, cap integer, id integer) RETURNS bigint
    LANGUAGE plpgsql
    AS $$
DECLARE
    new_lobby_id bigint; -- РџРµСЂРµРјРµРЅРЅР°СЏ РґР»СЏ С…СЂР°РЅРµРЅРёСЏ РЅРѕРІРѕРіРѕ lobby_id
BEGIN
    -- Р’СЃС‚Р°РІРєР° РЅРѕРІРѕР№ Р·Р°РїРёСЃРё РІ С‚Р°Р±Р»РёС†Сѓ Lobbies
    INSERT INTO Lobbies(lobby_name, capacity, admin_id, active)
    VALUES (name, cap, id, true)
    RETURNING lobby_id INTO new_lobby_id; -- РџРѕР»СѓС‡РµРЅРёРµ РЅРѕРІРѕРіРѕ lobby_id

    RETURN new_lobby_id;
END;

$$;


--
-- Name: add_user(text, text, bigint); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.add_user(p_nickname text, p_login text, p_password bigint) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    INSERT INTO Players (Nickname, Login, Password)
    VALUES (p_nickname, p_login, p_password);
END;
$$;


--
-- Name: add_user_in_lobby(bigint, bigint); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.add_user_in_lobby(p_id bigint, l_id bigint) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    insert into LobbyMembers(player_id,lobby_id,plase,points,change_rating)
    VALUES (p_id,l_id,0,0,0);
END;
$$;


--
-- Name: authorization(text, bigint); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public."authorization"(log text, pass bigint) RETURNS TABLE(user_count integer, user_id integer, nickname text, rating bigint)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY
    SELECT 
        CASE WHEN EXISTS (
            SELECT 1 
            FROM Players 
            WHERE login = log AND password = pass
        ) THEN 1 ELSE 0 END,
        p.id,
        p.nickname,
        p.rating
    FROM Players p
    WHERE p.login = log AND p.password = pass;

    -- Если пользователь не найден, явно возвращаем 0 и NULL
    IF NOT FOUND THEN
        RETURN QUERY SELECT 0, NULL, NULL, NULL;
    END IF;
END;
$$;


--
-- Name: get_info_p(integer); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.get_info_p(target_id integer) RETURNS TABLE(login text, nickname text, rating bigint)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY 
    SELECT 
        p.login, 
        p.nickname, 
        p.rating 
    FROM Players p 
    WHERE p.id = target_id;
END;
$$;


--
-- Name: get_info_p(text); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.get_info_p(log text) RETURNS TABLE(id integer, nickname text, rating bigint)
    LANGUAGE plpgsql
    AS $$
BEGIN
    RETURN QUERY 
    SELECT 
        p.id, 
        p.nickname, 
        p.rating 
    FROM Players p 
    WHERE p.login = log;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: lobbies; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lobbies (
    lobby_id bigint NOT NULL,
    lobby_name text NOT NULL,
    capacity integer,
    date timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    admin_id integer,
    active boolean
);


--
-- Name: lobbies_lobby_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.lobbies_lobby_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: lobbies_lobby_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.lobbies_lobby_id_seq OWNED BY public.lobbies.lobby_id;


--
-- Name: lobbymembers; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.lobbymembers (
    player_id bigint NOT NULL,
    lobby_id bigint NOT NULL,
    joined_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    plase integer,
    points integer,
    change_rating integer
);


--
-- Name: players; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.players (
    id integer NOT NULL,
    login text NOT NULL,
    password bigint NOT NULL,
    nickname text,
    rating bigint DEFAULT 0
);


--
-- Name: players_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.players_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: players_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.players_id_seq OWNED BY public.players.id;


--
-- Name: lobbies lobby_id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lobbies ALTER COLUMN lobby_id SET DEFAULT nextval('public.lobbies_lobby_id_seq'::regclass);


--
-- Name: players id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.players ALTER COLUMN id SET DEFAULT nextval('public.players_id_seq'::regclass);


--
-- Data for Name: lobbies; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.lobbies (lobby_id, lobby_name, capacity, date, admin_id, active) FROM stdin;
29	123	0	2025-02-16 17:23:07.229003	10	t
\.


--
-- Data for Name: lobbymembers; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.lobbymembers (player_id, lobby_id, joined_at, plase, points, change_rating) FROM stdin;
9	29	2025-02-16 17:23:21.562828	0	0	0
\.


--
-- Data for Name: players; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.players (id, login, password, nickname, rating) FROM stdin;
9	k@k	66566	karpim	0
10	v@v	66566	Вова	0
\.


--
-- Name: lobbies_lobby_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.lobbies_lobby_id_seq', 29, true);


--
-- Name: players_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.players_id_seq', 10, true);


--
-- Name: lobbies lobbies_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lobbies
    ADD CONSTRAINT lobbies_pkey PRIMARY KEY (lobby_id);


--
-- Name: lobbymembers lobbymembers_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lobbymembers
    ADD CONSTRAINT lobbymembers_pkey PRIMARY KEY (player_id, lobby_id);


--
-- Name: players players_login_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.players
    ADD CONSTRAINT players_login_key UNIQUE (login);


--
-- Name: players players_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.players
    ADD CONSTRAINT players_pkey PRIMARY KEY (id);


--
-- Name: lobbies lobbies_admin_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lobbies
    ADD CONSTRAINT lobbies_admin_id_fkey FOREIGN KEY (admin_id) REFERENCES public.players(id);


--
-- Name: lobbymembers lobbymembers_lobby_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lobbymembers
    ADD CONSTRAINT lobbymembers_lobby_id_fkey FOREIGN KEY (lobby_id) REFERENCES public.lobbies(lobby_id) ON DELETE CASCADE;


--
-- Name: lobbymembers lobbymembers_player_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.lobbymembers
    ADD CONSTRAINT lobbymembers_player_id_fkey FOREIGN KEY (player_id) REFERENCES public.players(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

