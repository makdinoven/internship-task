# Internship-task

[Description](https://docs.google.com/document/d/1nbgHHTi-cqoDHgwICfiRUnYepspa-lMJGjguM1sMZjk)

## Для запуска проекта
#### *Убедитесь, что docker и docker compose установлен

`docker compose up --build -d `


## Миграции 
### *Для Linux(Ubuntu)
### Инициализация новой миграции 
`sudo docker compose exec app alembic revision --autogenerate -m "NAME"`

### Применение миграции
`sudo docker compose exec app alembic upgrade head`

## Cнимки БД
### *Для Linux(Ubuntu)
#### Применение последнего дампа 
` sudo bash ./scripts/restore.sh`

#### Создание нового дампа

` sudo bash ./scripts/dump.sh`


