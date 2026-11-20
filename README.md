# M.A.R.S. - Multi-Agent Research System

Research a topic with a coordinated LangGraph workflow, compare retrieved
sources for conflicts, produce a cited report, and independently check claims.

## How it works

1. **Planner** turns the topic into focused research questions.
2. **Searcher** retrieves source excerpts and URLs from Tavily, deduplicates
   results, and records partial search failures.
3. **Conflict detector** identifies disagreements and keeps only conflicts
   citing two distinct retrieved sources.
4. **Critic** assesses question coverage and source quality; weak coverage
   triggers another targeted retrieval pass.
5. **Synthesizer** writes a report with inline `[S1]` citations and a source
   list, prioritizing primary, official, and reputable evidence.
6. **Fact-checker** extracts checkable report claims and searches for separate
   evidence. Verdicts are `Supported`, `Unsupported`, or `Uncertain`; citations
   must point to a retrieved source.

The workflow reports search limitations and treats unsupported claims as
uncertain rather than presenting them as verified facts. Source-quality
assessment is automated and should not replace human review for high-stakes
decisions.

Reports include a Trust & Verification Dashboard with supported, uncertain,
and unsupported claim counts, per-claim confidence bands, and a breakdown of
source URL suffixes (`.edu`, `.gov`, `.org`, `.com`, and other). Confidence is
the model's assessment, not a calibrated probability; URL categories do not
establish source accuracy or independence.

## Setup

1. Create a Supabase project. In its Authentication settings, enable email
   sign-in and configure the Google and GitHub providers you want to offer.
2. Copy `.env.example` to `.env` and set `GROQ_API_KEY`, `TAVILY_API_KEY`,
   `SUPABASE_URL`, and `SUPABASE_ANON_KEY`. Keep `.env` local; it is excluded
   from Git. Use the Supabase anon/publishable key, never the service-role key.
3. Add `https://fact-checker-agent-hgqyvxqwdxnaz6b5yjg8x2.streamlit.app/` to
   Supabase's allowed redirect URLs. Set `SUPABASE_REDIRECT_URL` to the
   M.A.R.S. live UI origin; for local development, use
   `http://localhost:8501` and add it to the allowlist. In the Google and GitHub
   developer consoles, use the callback URL shown by Supabase.
4. Install dependencies: `pip install -r requirements.txt`.
5. Start the API: `uvicorn api.app:app --reload --port 8000`.
6. In another terminal, start the UI: `streamlit run ui/streamlit_app.py`.
7. Open `http://localhost:8501`, then create an account with email or continue
   with Google or GitHub. Email confirmation follows your Supabase settings.

Use the sidebar's **Dark mode** switch to change the full dashboard, report
views, forms, and cards to the dark palette.

Optionally attach a text-based PDF (up to 10 MB and 100 pages) to a research
run. Extracted text is limited to 25,000 characters and treated as user
context, not independent evidence; the agents compare it with web sources and
verify claims. Scanned PDFs require OCR before upload. Completed reports can
be downloaded as Markdown from the report views.

The API endpoint is `POST /research/stream` with JSON
`{"topic": "Your research question"}` and a Supabase bearer access token. It
streams progress and the final report as server-sent events. `GET /` is a
public health check.

## Tests

Run `pytest`.

## Deployment

The included Dockerfile can be deployed to Cloud Run. Provide the API keys
through environment variables or secret references; do not bake credentials
into the container image. Deploy the Streamlit frontend separately and update
its API URL for the deployed backend.