--
-- PostgreSQL database dump
--

-- Dumped from database version 15.10 (Debian 15.10-1.pgdg120+1)
-- Dumped by pg_dump version 15.10 (Debian 15.10-1.pgdg120+1)

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
-- Name: currencyenum; Type: TYPE; Schema: public; Owner: user
--

CREATE TYPE public.currencyenum AS ENUM (
    'USD',
    'EUR',
    'AUD',
    'CAD',
    'ARS',
    'PLN',
    'BTC',
    'ETH',
    'DOGE',
    'USDT'
);


ALTER TYPE public.currencyenum OWNER TO "user";

--
-- Name: transactionstatusenum; Type: TYPE; Schema: public; Owner: user
--

CREATE TYPE public.transactionstatusenum AS ENUM (
    'processed',
    'roll_backed',
    'success'
);


ALTER TYPE public.transactionstatusenum OWNER TO "user";

--
-- Name: transactiontypeenum; Type: TYPE; Schema: public; Owner: user
--

CREATE TYPE public.transactiontypeenum AS ENUM (
    'DEPOSIT',
    'WITHDRAWAL'
);


ALTER TYPE public.transactiontypeenum OWNER TO "user";

--
-- Name: userstatusenum; Type: TYPE; Schema: public; Owner: user
--

CREATE TYPE public.userstatusenum AS ENUM (
    'ACTIVE',
    'BLOCKED'
);


ALTER TYPE public.userstatusenum OWNER TO "user";

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: transaction; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.transaction (
    id integer NOT NULL,
    user_id integer NOT NULL,
    currency public.currencyenum,
    amount numeric,
    type public.transactiontypeenum NOT NULL,
    status public.transactionstatusenum NOT NULL,
    created timestamp without time zone
);


ALTER TABLE public.transaction OWNER TO "user";

--
-- Name: transaction_id_seq; Type: SEQUENCE; Schema: public; Owner: user
--

CREATE SEQUENCE public.transaction_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.transaction_id_seq OWNER TO "user";

--
-- Name: transaction_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: user
--

ALTER SEQUENCE public.transaction_id_seq OWNED BY public.transaction.id;


--
-- Name: user; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public."user" (
    id integer NOT NULL,
    email character varying NOT NULL,
    status public.userstatusenum NOT NULL,
    created timestamp without time zone
);


ALTER TABLE public."user" OWNER TO "user";

--
-- Name: user_balance; Type: TABLE; Schema: public; Owner: user
--

CREATE TABLE public.user_balance (
    id integer NOT NULL,
    user_id integer NOT NULL,
    currency character varying,
    amount numeric,
    created timestamp without time zone
);


ALTER TABLE public.user_balance OWNER TO "user";

--
-- Name: user_balance_id_seq; Type: SEQUENCE; Schema: public; Owner: user
--

CREATE SEQUENCE public.user_balance_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_balance_id_seq OWNER TO "user";

--
-- Name: user_balance_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: user
--

ALTER SEQUENCE public.user_balance_id_seq OWNED BY public.user_balance.id;


--
-- Name: user_id_seq; Type: SEQUENCE; Schema: public; Owner: user
--

CREATE SEQUENCE public.user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.user_id_seq OWNER TO "user";

--
-- Name: user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: user
--

ALTER SEQUENCE public.user_id_seq OWNED BY public."user".id;


--
-- Name: transaction id; Type: DEFAULT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.transaction ALTER COLUMN id SET DEFAULT nextval('public.transaction_id_seq'::regclass);


--
-- Name: user id; Type: DEFAULT; Schema: public; Owner: user
--

ALTER TABLE ONLY public."user" ALTER COLUMN id SET DEFAULT nextval('public.user_id_seq'::regclass);


--
-- Name: user_balance id; Type: DEFAULT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.user_balance ALTER COLUMN id SET DEFAULT nextval('public.user_balance_id_seq'::regclass);


--
-- Data for Name: transaction; Type: TABLE DATA; Schema: public; Owner: user
--

COPY public.transaction (id, user_id, currency, amount, type, status, created) FROM stdin;
\.


--
-- Data for Name: user; Type: TABLE DATA; Schema: public; Owner: user
--

COPY public."user" (id, email, status, created) FROM stdin;
1	user@example.com	ACTIVE	2025-02-08 12:06:11.540923
\.


--
-- Data for Name: user_balance; Type: TABLE DATA; Schema: public; Owner: user
--

COPY public.user_balance (id, user_id, currency, amount, created) FROM stdin;
1	1	CAD	0	2025-02-08 12:06:11.554702
2	1	EUR	0	2025-02-08 12:06:11.557892
3	1	DOGE	0	2025-02-08 12:06:11.559609
5	1	PLN	0	2025-02-08 12:06:11.563254
6	1	USDT	0	2025-02-08 12:06:11.56522
7	1	BTC	0	2025-02-08 12:06:11.567337
8	1	ARS	0	2025-02-08 12:06:11.569301
9	1	ETH	0	2025-02-08 12:06:11.571022
10	1	AUD	0	2025-02-08 12:06:11.572735
4	1	USD	5	2025-02-08 12:06:11.561411
\.


--
-- Name: transaction_id_seq; Type: SEQUENCE SET; Schema: public; Owner: user
--

SELECT pg_catalog.setval('public.transaction_id_seq', 1, false);


--
-- Name: user_balance_id_seq; Type: SEQUENCE SET; Schema: public; Owner: user
--

SELECT pg_catalog.setval('public.user_balance_id_seq', 10, true);


--
-- Name: user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: user
--

SELECT pg_catalog.setval('public.user_id_seq', 1, true);


--
-- Name: transaction transaction_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.transaction
    ADD CONSTRAINT transaction_pkey PRIMARY KEY (id);


--
-- Name: user_balance user_balance_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.user_balance
    ADD CONSTRAINT user_balance_pkey PRIMARY KEY (id);


--
-- Name: user user_email_key; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_email_key UNIQUE (email);


--
-- Name: user user_pkey; Type: CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);


--
-- Name: user_balance user_balance_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: user
--

ALTER TABLE ONLY public.user_balance
    ADD CONSTRAINT user_balance_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- PostgreSQL database dump complete
--

