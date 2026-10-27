curl -s -X POST localhost:8000/notebooks/1/chat -H 'Content-Type: application/json' \
  -d '{"question":"How many documents did the BioASQ experiment use?","k":8}' | jq

  
docker compose exec db psql -U postgres -d notebooklm -c \
  "select question, model, prompt_tokens, completion_tokens, latency_ms, citations from query_logs order by id desc limit 5;"

docker compose exec backend python scripts/show_prompt.py 1 "How many documents did the BioASQ experiment use?" --k 8


docker compose exec db psql -U postgres -d notebooklm -c "select question, model, prompt_tokens, completion_tokens, latency_ms, citations from query_logs order by id desc;"