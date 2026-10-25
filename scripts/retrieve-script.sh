NB=6
ask() { curl -s -X POST localhost:8000/notebooks/$NB/retrieve \
  -H 'Content-Type: application/json' \
  -d "{\"question\": \"$1\", \"k\": ${2:-5}}" \
| jq -r '.chunks | to_entries[] | "\(.key+1)  \(.value.score|tostring|.[0:5])  \(.value.filename) p\(.value.page_number) #\(.value.chunk_index)  \(.value.text|gsub("\n";" "))"'; }

ask "How many documents did the BioASQ experiment use?" 10