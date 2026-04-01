# Система документооборота --- Полная документация

------------------------------------------------------------------------

# 1. Обзор системы

Система предназначена для управления документами внутри организации: -
создание документов - назначение исполнителей - контроль сроков -
история изменений - встроенный чат - уведомления в реальном времени

------------------------------------------------------------------------

# 2. Архитектура

## Слои системы

    API → Service → Repository → Database

## Поток запроса

1.  Клиент отправляет запрос\
2.  API валидирует вход\
3.  Service применяет бизнес-логику\
4.  Repository работает с БД\
5.  Ответ возвращается клиенту

------------------------------------------------------------------------

# 3. Backend

## 3.1 Модели данных

### User

-   id (UUID)
-   email
-   password_hash
-   full_name
-   role_id
-   is_active
-   created_at

### Role / Permission / RolePermission

RBAC модель: - роли: ADMIN, MANAGER, USER - права: document.read,
document.create и др.

### Document

-   id
-   title
-   file_name
-   file_path
-   description
-   status
-   author_id
-   executor_id
-   deadline
-   is_overdue
-   is_deleted

Статусы:

    NEW → IN_PROGRESS → ON_REVIEW → DONE

### DocumentHistory

Хранит изменения: - поле - старое значение - новое значение -
пользователь - дата

### DocumentMessage

Чат внутри документа

### DocumentWatcher

Наблюдатели документа

### Notification

-   user_id
-   type
-   entity_id
-   is_read
-   created_at

------------------------------------------------------------------------

## 3.2 Repository слой

### DocumentRepository

#### get_by_id

Получение документа

#### get_list

Функции: - фильтрация (status, executor, search, deadline) - контроль
доступа: - ADMIN → все документы - USER → только свои

Используется:

    aliased(User)

------------------------------------------------------------------------

## 3.3 Service слой

### DocumentService

#### create_document

-   создание документа
-   запись истории
-   уведомления

#### update_document

-   сравнение изменений
-   запись истории
-   обновление данных
-   генерация событий

Типы событий: - assign - status_change - deadline_change

------------------------------------------------------------------------

## 3.4 API

### Auth

    POST /auth/login

### Documents

    GET    /documents
    POST   /documents
    GET    /documents/{id}
    PATCH  /documents/{id}
    DELETE /documents/{id}
    GET    /documents/{id}/history

### Watchers

    POST /watchers
    DELETE /watchers
    GET /watchers

### Chats

    GET /chats
    POST /chats/{doc_id}/messages
    WS  /ws/{doc_id}

### Users

    POST /users
    GET /users
    PATCH /users
    DELETE /users

### Notifications

    GET /users/me/notifications
    PATCH /users/me/notifications
    WS  /ws/notifications

------------------------------------------------------------------------

## 3.5 WebSocket

ConnectionManager: - user_id → connections - doc_id → connections

Методы: - connect - disconnect - send_to_user - send_to_document

------------------------------------------------------------------------

## 3.6 Worker

process_overdue_documents: - поиск просроченных - установка is_overdue -
отправка уведомлений - снятие флага при исправлении

------------------------------------------------------------------------

## 3.7 Docker

    docker compose up -d --build

------------------------------------------------------------------------

# 4. Frontend

## 4.1 Архитектура

SSR (Jinja2) + JavaScript

-   сервер генерирует HTML
-   JS работает с API
-   WebSocket обновляет данные

------------------------------------------------------------------------

## 4.2 Страницы

### base.html

-   layout
-   websocket
-   toast уведомления

### login.html

-   авторизация через fetch
-   JWT в cookie

### index.html

-   список документов
-   фильтры
-   таблица / карточки

### document_detail.html

-   данные документа
-   история
-   чат (WebSocket)

### notifications.html

-   список уведомлений
-   отметка прочитанных

### users.html

-   управление пользователями
-   роли и доступы

------------------------------------------------------------------------

## 4.3 WebSocket

Используется для: - уведомлений - чата

Особенности: - авто-реконнект - обновление UI без reload

------------------------------------------------------------------------

## 4.4 UI стек

-   TailwindCSS
-   FontAwesome
-   Vanilla JS

------------------------------------------------------------------------

# 5. Безопасность

-   JWT (HttpOnly cookie)
-   RBAC
-   проверка прав на уровне API

------------------------------------------------------------------------

# 6. Итог

Система реализует: - документооборот - чат - уведомления - роли и
права - WebSocket - фоновые задачи

Архитектура масштабируемая и готова к расширению.
