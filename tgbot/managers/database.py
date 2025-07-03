from core.database import Database
import logging

class DatabaseManager:


    def __init__(self):
        pass

    logger = logging.getLogger(__name__)

    @staticmethod
    def check_user(user_id):
        with Database() as db:
            if db.connect():
                result = db.execute(
                    "SELECT * FROM users WHERE telegram_id = %s",
                    (user_id,),
                    fetch_one=True
                )
                return bool(result)

    @staticmethod
    def register_user(user_id, username, first_name):
        with Database() as db:
            if db.connect():
                return db.execute(
                    "INSERT INTO users (telegram_id, username, first_name) VALUES (%s, %s, %s)",
                    (user_id, username, first_name)
                )

    @staticmethod
    def get_user_by_telegram_id(telegram_id):
        with Database() as db:
            if db.connect():
                result = db.execute(
                    "SELECT telegram_id FROM users WHERE telegram_id = %s",
                    (telegram_id,),
                    fetch_one=True
                )
                return result

    @staticmethod
    def get_all_roles(user_id):
        with Database() as db:
            if db.connect():
                results = db.execute(
                    "SELECT role FROM user_roles WHERE user_id = %s",
                    (user_id,)
                )
                return [role[0] for role in results] if results else []

    @staticmethod
    def get_active_role(user_id):
        with Database() as db:
            if db.connect():
                result = db.execute(
                    "SELECT role FROM user_roles WHERE user_id = %s AND is_active = 1",
                    (user_id,),
                    fetch_one=True
                )
                return result[0] if result else None

    @staticmethod
    def save_user_role(user_id, role):
        with Database() as db:
            if db.connect():
                if DatabaseManager.user_has_role(user_id, role):
                    return DatabaseManager.switch_active_role(user_id, role)
                else:
                    db.execute(
                        "UPDATE user_roles SET is_active = 0 WHERE user_id = %s",
                        (user_id,)
                    )
                    return db.execute(
                        "INSERT INTO user_roles (user_id, role, is_active) VALUES (%s, %s, 1)",
                        (user_id, role)
                    )

    @staticmethod
    def user_has_role(user_id, role):
        with Database() as db:
            if db.connect():
                result = db.execute(
                    "SELECT * FROM user_roles WHERE user_id = %s AND role = %s",
                    (user_id, role),
                    fetch_one=True
                )
                return bool(result)

    @staticmethod
    def switch_active_role(user_id, new_role):
        with Database() as db:
            if db.connect():
                db.execute(
                    "UPDATE user_roles SET is_active = 0 WHERE user_id = %s",
                    (user_id,)
                )
                return db.execute(
                    "UPDATE user_roles SET is_active = 1 WHERE user_id = %s AND role = %s",
                    (user_id, new_role)
                )

    @staticmethod
    def is_admin(user_id):
        with Database() as db:
            if db.connect():
                result = db.execute(
                    "SELECT 1 FROM user_roles WHERE user_id = %s AND role = 'admin'",
                    (user_id,),
                    fetch_one=True
                )
                return bool(result)

    @staticmethod
    def get_available_roles(user_id):
        all_roles = ['client', 'barber']
        current_roles = DatabaseManager.get_all_roles(user_id)
        return [role for role in all_roles if role not in current_roles]

    @staticmethod
    def get_pending_profiles(page=0, per_page=10, city_id=None):
        with Database() as db:
            if db.connect():
                offset = page * per_page
                query = """
                    SELECT 
                        barbers.id, 
                        barbers.user_id, 
                        users.username, 
                        cities.name AS city_name, 
                        barbers.experience_years, 
                        barbers.instagram, 
                        barbers.whatsapp, 
                        barbers.telegram,
                        (SELECT COUNT(*) FROM barber_portfolio WHERE barber_portfolio.barber_id = barbers.id) AS photos_count,
                        users.first_name
                    FROM 
                        barbers
                    JOIN 
                        users ON barbers.user_id = users.telegram_id
                    JOIN 
                        cities ON barbers.city_id = cities.id
                    WHERE 
                        barbers.status = 'pending'
                """
                params = []
                if city_id:
                    query += " AND barbers.city_id = %s"
                    params.append(city_id)

                query += " LIMIT %s OFFSET %s"
                params.extend([per_page, offset])

                return db.execute(query, tuple(params))
        return []

    @staticmethod
    def barber_exists(user_id):
        with Database() as db:
            if db.connect():
                result = db.execute(
                    "SELECT id FROM barbers WHERE user_id = %s",
                    (user_id,),
                    fetch_one=True
                )
                return bool(result)

    @staticmethod
    def get_barber_by_user_id(user_id):
        with Database() as db:
            if db.connect():
                result = db.execute(
                    "SELECT id FROM barbers WHERE user_id = %s",
                    (user_id,),
                    fetch_one=True
                )
                return result

    @staticmethod
    def insert_barber(user_id, city_id, metro_id, description, experience, instagram, whatsapp, telegram, status):
        """Добавляет нового барбера в базу со статусом pending"""
        try:
            with Database() as db:
                if db.connect():
                    db.execute(
                        "INSERT INTO barbers (user_id, city_id, metro_id, description, "
                        "experience_years, instagram, whatsapp, telegram, status) "
                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                        (user_id, city_id, metro_id, description,
                         experience, instagram, whatsapp, telegram, status)
                    )
                    result = db.execute("SELECT LAST_INSERT_ID()", fetch_one=True)
                    return result[0] if result else None
        except Exception as e:
            logger.error(f"Error inserting barber: {e}")
            return None

    @staticmethod
    def update_barber(barber_id, city_id, metro_id, description, experience, instagram, whatsapp, telegram, status):
        """Обновляет данные барбера со статусом pending"""
        try:
            with Database() as db:
                if db.connect():
                    affected_rows = db.execute(
                        "UPDATE barbers SET city_id = %s, metro_id = %s, description = %s, "
                        "experience_years = %s, instagram = %s, whatsapp = %s, telegram = %s, status = %s "
                        "WHERE id = %s",
                        (city_id, metro_id, description, experience,
                         instagram, whatsapp, telegram, status, barber_id)
                    )
                    return affected_rows > 0
        except Exception as e:
            logger.error(f"Error updating barber: {e}")
            return False
    @staticmethod
    def update_barber_status(barber_id, status):
        with Database() as db:
            if db.connect():
                return db.execute(
                    "UPDATE barbers SET status = %s WHERE id = %s",
                    (status, barber_id)
                )

    @staticmethod
    def get_barber_user_id(barber_id):
        with Database() as db:
            if db.connect():
                result = db.execute(
                    "SELECT user_id FROM barbers WHERE id = %s",
                    (barber_id,),
                    fetch_one=True
                )
                return result[0] if result else None

    @staticmethod
    def delete_barber_data(user_id):
        """Сбрасывает анкету барбера к начальному состоянию, сохраняя user_id и рейтинг"""
        with Database() as db:
            if db.connect():
                # Проверяем существование анкеты
                barber = db.execute(
                    "SELECT id FROM barbers WHERE user_id = %s",
                    (user_id,),
                    fetch_one=True
                )
                if not barber:
                    return False

                barber_id = barber[0]

                # Удаляем связанные данные (услуги и фото)
                db.execute("DELETE FROM barber_services WHERE barber_id = %s", (barber_id,))
                db.execute("DELETE FROM barber_portfolio WHERE barber_id = %s", (barber_id,))

                # Обновляем основную анкету, сохраняя рейтинг
                db.execute(
                    """
                    UPDATE barbers 
                    SET 
                        city_id = NULL,
                        metro_id = NULL,
                        description = NULL,
                        experience_years = NULL,
                        instagram = NULL,
                        whatsapp = NULL,
                        telegram = NULL,
                        status = 'pending',
                        
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (barber_id,)
                )

                return True
        return False
    @staticmethod
    def get_barber_full_data_by_user_id(user_id):
        """Возвращает полные данные барбера, включая метро (если есть)"""
        with Database() as db:
            if db.connect():
                result = db.execute(
                    """
                    SELECT 
                        barbers.id, 
                        barbers.user_id, 
                        users.username, 
                        cities.name AS city_name, 
                        barbers.experience_years,
                        barbers.instagram, 
                        barbers.whatsapp, 
                        barbers.telegram,
                        users.first_name,
                        barbers.description,
                        metro_stations.name AS metro_name,
                        barbers.metro_id,
                        (SELECT COUNT(*) FROM barber_portfolio WHERE barber_id = barbers.id) AS photos_count
                    FROM 
                        barbers
                    JOIN 
                        users ON barbers.user_id = users.telegram_id
                    JOIN 
                        cities ON barbers.city_id = cities.id
                    LEFT JOIN
                        metro_stations ON barbers.metro_id = metro_stations.id
                    WHERE 
                        barbers.user_id = %s
                    """,
                    (user_id,),
                    fetch_one=True
                )
                if result:
                    return {
                        'id': result[0],
                        'user_id': result[1],
                        'username': result[2],
                        'city_name': result[3],
                        'experience_years': result[4],
                        'instagram': result[5],
                        'whatsapp': result[6],
                        'telegram': result[7],
                        'first_name': result[8],
                        'description': result[9],
                        'metro_name': result[10] if result[10] else None,  # Может быть None
                        'metro_id': result[11] if result[11] else None,     # Может быть None
                        'photos_count': result[12] or 0                     # Количество фото
                    }
        return None
    @staticmethod
    def get_barber_photos(barber_id):
        with Database() as db:
            if db.connect():
                return db.execute(
                    "SELECT photo_url FROM barber_portfolio WHERE barber_id = %s ORDER BY position",
                    (barber_id,)
                )
        return []

    @staticmethod
    def insert_barber_portfolio(barber_id, photo_url, position):
        with Database() as db:
            if db.connect():
                return db.execute(
                    """
                    INSERT INTO barber_portfolio (barber_id, photo_url, position)
                    VALUES (%s, %s, %s)
                    """,
                    (barber_id, photo_url, position)
                )

    @staticmethod
    def delete_barber_portfolio(barber_id):
        with Database() as db:
            if db.connect():
                return db.execute(
                    "DELETE FROM barber_portfolio WHERE barber_id = %s",
                    (barber_id,)
                )

    @staticmethod
    def get_city_id_by_name(city_name):
        with Database() as db:
            if db.connect():
                result = db.execute(
                    "SELECT id FROM cities WHERE LOWER(name) = %s",
                    (city_name.lower(),),
                    fetch_one=True
                )
                return result[0] if result else None

    @staticmethod
    def get_category_id_by_type(category_type):
        with Database() as db:
            if db.connect():
                result = db.execute(
                    "SELECT id FROM haircut_categories WHERE type = %s",
                    (category_type,),
                    fetch_one=True
                )
                return result[0] if result else None

    @staticmethod
    def insert_barber_service(barber_id, category_id, name, price):
        with Database() as db:
            if db.connect():
                return db.execute(
                    """
                    INSERT INTO barber_services (barber_id, category_id, name, price)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (barber_id, category_id, name, price)
                )

    @staticmethod
    def delete_barber_services(barber_id):
        with Database() as db:
            if db.connect():
                return db.execute(
                    "DELETE FROM barber_services WHERE barber_id = %s",
                    (barber_id,)
                )

    @staticmethod
    def is_user_banned(user_id):
        with Database() as db:
            if db.connect():
                result = db.execute(
                    "SELECT status FROM barbers WHERE user_id = %s",
                    (user_id,),
                    fetch_one=True
                )
                if result and result[0] == "banned":
                    return True
        return False

    @staticmethod
    def get_barber_by_id(barber_id):
        with Database() as db:
            if db.connect():
                result = db.execute(
                    """
                    SELECT 
                        barbers.id, 
                        barbers.user_id, 
                        users.username, 
                        cities.name AS city_name, 
                        barbers.experience_years,
                        barbers.instagram, 
                        barbers.whatsapp, 
                        barbers.telegram,
                        (SELECT COUNT(*) FROM barber_portfolio WHERE barber_portfolio.barber_id = barbers.id) AS photos_count,
                        users.first_name,
                        barbers.description
                    FROM 
                        barbers
                    JOIN 
                        users ON barbers.user_id = users.telegram_id
                    JOIN 
                        cities ON barbers.city_id = cities.id
                    WHERE 
                        barbers.id = %s
                    """,
                    (barber_id,),
                    fetch_one=True
                )
                if result:
                    return {
                        'id': result[0],
                        'user_id': result[1],
                        'username': result[2],
                        'city_name': result[3],
                        'experience_years': result[4],
                        'instagram': result[5],
                        'whatsapp': result[6],
                        'telegram': result[7],
                        'photos_count': result[8],
                        'first_name': result[9],
                        'description': result[10],  # теперь description всегда есть!
                    }
        return None

    @staticmethod
    def get_barber_services(barber_id):
        """Возвращает список услуг барбера в формате (название, цена)"""
        with Database() as db:
            if db.connect():
                results = db.execute(
                    "SELECT name, price FROM barber_services WHERE barber_id = %s ORDER BY price",
                    (barber_id,)
                )
                return results if results else []
        return []

    @staticmethod
    def get_barber_status(user_id):
        with Database() as db:
            if db.connect():
                result = db.execute(
                    "SELECT status FROM barbers WHERE user_id = %s",
                    (user_id,),
                    fetch_one=True
                )
                return result[0] if result else None
        return None

    @staticmethod
    def get_all_cities():
        with Database() as db:
            if db.connect():
                results = db.execute(
                    "SELECT name FROM cities WHERE is_active = 1"
                )
                return [row[0] for row in results] if results else []

    @staticmethod
    def save_user_city_selection(user_id, city_id):
        with Database() as db:
            if db.connect():
                db.execute(
                    "DELETE FROM user_city_selections WHERE user_id = %s",
                    (user_id,)
                )
                return db.execute(
                    "INSERT INTO user_city_selections (user_id, city_id) VALUES (%s, %s)",
                    (user_id, city_id)
                )

    @staticmethod
    def get_active_barbers(page=0, per_page=10, city_id=None):
        with Database() as db:
            if db.connect():
                offset = page * per_page
                query = """
                    SELECT 
                        barbers.id, 
                        barbers.user_id, 
                        users.username, 
                        cities.name AS city_name, 
                        barbers.experience_years, 
                        barbers.instagram, 
                        barbers.whatsapp, 
                        barbers.telegram,
                        (SELECT COUNT(*) FROM barber_portfolio WHERE barber_portfolio.barber_id = barbers.id) AS photos_count,
                        users.first_name
                    FROM 
                        barbers
                    JOIN 
                        users ON barbers.user_id = users.telegram_id
                    JOIN 
                        cities ON barbers.city_id = cities.id
                    WHERE 
                        barbers.status = 'active'
                """
                params = []
                if city_id:
                    query += " AND barbers.city_id = %s"
                    params.append(city_id)
                query += " LIMIT %s OFFSET %s"
                params.extend([per_page, offset])
                return db.execute(query, tuple(params))
        return []

    @staticmethod
    def get_user_city_selection(user_id):
        with Database() as db:
            if db.connect():
                result = db.execute(
                    "SELECT city_id FROM user_city_selections WHERE user_id = %s ORDER BY selected_at DESC LIMIT 1",
                    (user_id,),
                    fetch_one=True
                )
                return result[0] if result else None
        return None

    @staticmethod
    def toggle_barber_visibility(user_id):
        """Переключает статус видимости анкеты барбера"""
        with Database() as db:
            if db.connect():
                result = db.execute(
                    "SELECT status FROM barbers WHERE user_id = %s",
                    (user_id,),
                    fetch_one=True
                )
                if not result:
                    return None
                current_status = result[0]
                new_status = 'hidden' if current_status == 'active' else 'active'
                db.execute(
                    "UPDATE barbers SET status = %s WHERE user_id = %s",
                    (new_status, user_id)
                )
                return new_status
        return None

    @staticmethod
    def get_barber_visibility_status(user_id):
        """Возвращает текущий статус видимости анкеты"""
        with Database() as db:
            if db.connect():
                result = db.execute(
                    "SELECT status FROM barbers WHERE user_id = %s",
                    (user_id,),
                    fetch_one=True
                )
                return result[0] if result else None
        return None

    @staticmethod
    def update_barber_status_by_user_id(user_id, new_status):
        """Обновляет статус анкеты барбера по user_id"""
        with Database() as db:
            if db.connect():
                return db.execute(
                    "UPDATE barbers SET status = %s WHERE user_id = %s",
                    (new_status, user_id)
                )
        return False

    @staticmethod
    def get_filtered_barbers(city_id, max_price=None, specialization_num=None, metro_id=None):
        """Возвращает отфильтрованных барберов с возможностью фильтрации по метро"""
        spec_map = {
            1: ['beard'],
            2: ['long'],
            3: ['short'],
            4: ['beard', 'short'],
            5: ['beard', 'long'],
            6: ['long', 'short'],
            7: ['beard', 'long', 'short'],
        }
        specs = spec_map.get(specialization_num, []) if specialization_num else []

        with Database() as db:
            if db.connect():
                query = """
                    SELECT 
                        b.id, b.user_id, u.username, c.name AS city_name, 
                        b.experience_years, b.instagram, b.whatsapp, b.telegram,
                        (SELECT COUNT(*) FROM barber_portfolio WHERE barber_id = b.id) AS photos_count,
                        u.first_name,
                        m.name as metro_name
                    FROM 
                        barbers b
                    JOIN 
                        users u ON b.user_id = u.telegram_id
                    JOIN 
                        cities c ON b.city_id = c.id
                    LEFT JOIN
                        metro_stations m ON b.metro_id = m.id
                    WHERE 
                        b.status = 'active'
                        AND b.city_id = %s
                """
                params = [city_id]

                # Добавляем фильтр по метро, если указано
                if metro_id:
                    query += " AND b.metro_id = %s"
                    params.append(metro_id)

                # Добавляем фильтр по специализации и цене, если указаны
                if specs and max_price is not None:
                    query += f"""
                        AND (
                            SELECT COUNT(DISTINCT hc.type)
                            FROM barber_services bs
                            JOIN haircut_categories hc ON bs.category_id = hc.id
                            WHERE bs.barber_id = b.id
                            AND hc.type IN ({','.join(['%s'] * len(specs))})
                            AND bs.price <= %s
                        ) = {len(specs)}
                    """
                    params.extend(specs)
                    params.append(max_price)

                results = db.execute(query, tuple(params))
                return results if results else []
        return []

    @staticmethod
    def get_haircuts_by_category(category_id):
        with Database() as db:
            if db.connect():
                return db.execute(
                    "SELECT id, name FROM haircut_guide WHERE category_id = %s",
                    (category_id,)
                )
        return []

    @staticmethod
    def get_haircut_details(haircut_id):
        with Database() as db:
            if db.connect():
                result = db.execute(
                    """SELECT hg.name, hg.description, hg.styling_tips, hc.type 
                    FROM haircut_guide hg
                    JOIN haircut_categories hc ON hg.category_id = hc.id
                    WHERE hg.id = %s""",
                    (haircut_id,),
                    fetch_one=True
                )
                if result:
                    return {
                        'name': result[0],
                        'description': result[1],
                        'styling_tips': result[2],
                        'category_type': result[3]
                    }
        return None

    @staticmethod
    def get_haircut_photos(haircut_id):
        with Database() as db:
            if db.connect():
                return db.execute(
                    "SELECT photo_url FROM haircut_guide_photos WHERE haircut_id = %s",
                    (haircut_id,)
                )
        return []

    @staticmethod
    def is_barber_favorite(client_id, barber_id):
        """Проверяет, есть ли барбер в избранном у клиента"""
        with Database() as db:
            if db.connect():
                result = db.execute(
                    "SELECT 1 FROM favorites WHERE client_id = %s AND barber_id = %s",
                    (client_id, barber_id),
                    fetch_one=True
                )
                return bool(result)
        return False

    @staticmethod
    def toggle_favorite(client_id, barber_id):
        """Добавляет/удаляет барбера из избранного"""
        with Database() as db:
            if db.connect():
                if DatabaseManager.is_barber_favorite(client_id, barber_id):
                    # Удаляем из избранного
                    return db.execute(
                        "DELETE FROM favorites WHERE client_id = %s AND barber_id = %s",
                        (client_id, barber_id)
                    )
                else:
                    # Добавляем в избранное
                    return db.execute(
                        "INSERT INTO favorites (client_id, barber_id) VALUES (%s, %s)",
                        (client_id, barber_id)
                    )
        return False

    @staticmethod
    def get_favorite_barbers(user_id):
        """Возвращает список избранных барберов для указанного пользователя (только активные)"""
        with Database() as db:
            if db.connect():
                query = """
                SELECT 
                    b.id, 
                    b.user_id, 
                    u.first_name, 
                    c.name AS city_name, 
                    b.instagram, 
                    b.whatsapp, 
                    b.telegram,
                    b.description,
                    b.experience_years,
                    b.status,
                    u.first_name as barber_first_name,
                    (SELECT COUNT(*) FROM barber_portfolio WHERE barber_id = b.id) AS photos_count,
                    (SELECT AVG(rating) FROM reviews WHERE barber_id = b.id) AS avg_rating,
                    (SELECT COUNT(*) FROM reviews WHERE barber_id = b.id) AS reviews_count
                FROM 
                    barbers b
                JOIN 
                    cities c ON b.city_id = c.id
                JOIN 
                    favorites f ON f.barber_id = b.id
                JOIN
                    users u ON b.user_id = u.telegram_id
                WHERE 
                    f.client_id = %s 
                    AND b.status = 'active'
                ORDER BY 
                    u.first_name
                """
                results = db.execute(query, (user_id,))

                if results:
                    return [{
                        'id': row[0],
                        'user_id': row[1],
                        'first_name': row[2],
                        'city_name': row[3],
                        'instagram': row[4],
                        'whatsapp': row[5],
                        'telegram': row[6],
                        'description': row[7],
                        'experience_years': row[8],
                        'status': row[9],
                        'barber_first_name': row[10],
                        'photos_count': row[11],
                        'avg_rating': float(row[12]) if row[12] else None,
                        'reviews_count': row[13]
                    } for row in results]
        return []
    @staticmethod
    def add_review(barber_id, client_id, rating, comment=None):
        with Database() as db:
            if db.connect():
                db.execute(
                    "INSERT INTO reviews (barber_id, client_id, rating, comment) VALUES (%s, %s, %s, %s)",
                    (barber_id, client_id, rating, comment)
                )
                # После добавления отзыва обновляем средний рейтинг
                DatabaseManager.update_barber_average_rating(barber_id)
                return True
        return False

    @staticmethod
    def update_barber_average_rating(barber_id):
        with Database() as db:
            if db.connect():
                result = db.execute(
                    "SELECT AVG(rating) FROM reviews WHERE barber_id = %s",
                    (barber_id,),
                    fetch_one=True
                )
                avg_rating = float(result[0]) if result and result[0] is not None else 0.0
                db.execute(
                    "UPDATE barbers SET rating = %s WHERE id = %s",
                    (avg_rating, barber_id)
                )
                return avg_rating
        return 0.0

    @staticmethod
    def add_barber_rating(barber_id, client_id, rating, comment=None):
        with Database() as db:
            if db.connect():
                return db.execute(
                    """
                    INSERT INTO reviews (barber_id, client_id, rating, comment)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE rating=%s, comment=%s
                    """,
                    (barber_id, client_id, rating)
                )
        return False

    @staticmethod
    def get_barber_average_rating(barber_id):
        with Database() as db:
            if db.connect():
                result = db.execute(
                    "SELECT AVG(rating), COUNT(*) FROM reviews WHERE barber_id = %s",
                    (barber_id,),
                    fetch_one=True
                )
                if result:
                    avg, count = result
                    return (round(avg, 2) if avg else None, count)
        return (None, 0)

    @staticmethod
    def get_barber_rating(barber_id):
        """Получает средний рейтинг барбера по отзывам"""
        cursor = None
        try:
            cursor = DatabaseManager.connection.cursor()
            cursor.execute("SELECT AVG(rating) FROM reviews WHERE barber_id = %s", (barber_id,))
            result = cursor.fetchone()
            return float(result[0]) if result and result[0] is not None else None
        except Exception as e:
            logger.error(f"Ошибка при получении рейтинга: {str(e)}")
            return None
        finally:
            if cursor:
                cursor.close()

    @staticmethod
    def get_city_name_by_id(city_id):
        """
        Возвращает название города по его city_id.
        """
        with Database() as db:
            if db.connect():
                result = db.execute(
                    "SELECT name FROM cities WHERE id = ?",
                    (city_id,)
                )
                if result and len(result) > 0:
                    # Если используете fetchone, то result[0] — кортеж (name,)
                    return result[0][0]
        return None

    @staticmethod
    def get_barber_portfolio(barber_id):
        """
        Возвращает список фото работ барбера (портфолио).
        :param barber_id: ID барбера
        :return: список кортежей (id, barber_id, file_id, created_at)
        """
        with Database() as db:
            if db.connect():
                results = db.execute(
                    """
                    SELECT id, barber_id, photo_url, position, created_at
                    FROM barber_portfolio
                    WHERE barber_id = %s
                    ORDER BY created_at ASC
                    """,
                    (barber_id,)
                )
                return results if results else []
        return []



    @staticmethod
    def city_has_metro(city_id):
        """Проверяет наличие метро в городе"""
        with Database() as db:
            if db.connect():
                result = db.execute(
                    "SELECT COUNT(*) FROM metro_stations "
                    "WHERE city_id = %s AND is_active = 1",
                    (city_id,),
                    fetch_one=True
                )
                return result[0] > 0 if result else False
        return False

    @staticmethod
    def get_metro_id_by_name(city_id, metro_name):
        """Ищет ID станции метро по названию"""
        with Database() as db:
            if db.connect():
                result = db.execute(
                    "SELECT id FROM metro_stations "
                    "WHERE city_id = %s AND name = %s AND is_active = 1",
                    (city_id, metro_name),
                    fetch_one=True
                )
                return result[0] if result else None
        return None

    # В классе DatabaseManager добавим:
    @staticmethod
    def get_pending_profiles_by_city(city_name, page=0, per_page=10):
        """Получает анкеты на модерацию по определенному городу с пагинацией"""
        offset = page * per_page
        query = """
        SELECT b.*, c.name as city_name 
        FROM barbers b
        JOIN cities c ON b.city_id = c.id
        WHERE b.status = 'pending' AND c.name = %s
        ORDER BY b.created_at DESC
        LIMIT %s OFFSET %s
        """
        return DatabaseManager.execute_query(query, (city_name, per_page, offset), fetch=True)

    @staticmethod
    def count_pending_profiles_by_city(city_name):
        """Считает количество анкеraт на модерации в определенном городе"""
        query = """
        SELECT COUNT(*) 
        FROM barbers b
        JOIN cities c ON b.city_id = c.id
        WHERE b.status = 'pending' AND c.name = %s
        """
        result = DatabaseManager.execute_query(query, (city_name,), fetch_one=True)
        return result[0] if result else 0

