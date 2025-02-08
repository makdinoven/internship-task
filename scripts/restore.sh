DB_CONTAINER="db"
DB_USER="user"
DB_NAME="task_db"


if [ -n "$1" ]; then
  DUMP_FILE="$1"
else
  DUMP_FILE=$(ls -1t dumps/dump_*.sql | head -n 1)
fi

if [ ! -f "$DUMP_FILE" ]; then
  echo "The dump file '$DUMP_FILE' not found!"
  exit 1
fi

echo "Database recovery '$DB_NAME' from file '$DUMP_FILE' ..."

cat "$DUMP_FILE" | docker exec -i "$DB_CONTAINER" psql -U "$DB_USER" "$DB_NAME"

if [ $? -eq 0 ]; then
  echo "Recovery success"
else
  echo "Error"
  exit 1
fi
