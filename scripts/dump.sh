DB_CONTAINER="db"
DB_USER="user"
DB_NAME="task_db"

mkdir -p dumps

DUMP_FILE="dumps/dump_$(date +'%Y-%m-%d_%H-%M-%S').sql"

echo "Create dump file '$DB_NAME' ..."

docker exec -t "$DB_CONTAINER" pg_dump -U "$DB_USER" "$DB_NAME" > "$DUMP_FILE"

if [ $? -eq 0 ]; then
  echo "Dump created: $DUMP_FILE"
else
  echo "Error"
  exit 1
fi
