run:
\tuvicorn app.main:app --reload

ui:
\tSTREAMLIT_SERVER_PORT=8501 streamlit run ui/app.py

test:
\tpytest -q
