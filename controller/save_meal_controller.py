import json
from database.db import get_db_connection

def save_meal_controller(user_id, data):
    details = data.get('details')
    if not details:
        return {"status": "error", "message": "No meal details provided."}, 400

    menu_name = details.get('menu_name')
    
    conn = get_db_connection()
    if not conn:
        return {"status": "error", "message": "Database connection failed."}, 500

    try:
        cursor = conn.cursor()

        check_sql = "SELECT id FROM saved_meals WHERE user_id = %s AND menu_name = %s"
        cursor.execute(check_sql, (user_id, menu_name))
        existing_meal = cursor.fetchone()

        if existing_meal:
            cursor.close()
            conn.close()
            return {
                "status": "exists", 
                "message": f"'{menu_name}' is already saved in your collection."
            }, 409  

        full_details_json = json.dumps(details)

        insert_sql = """
            INSERT INTO saved_meals (user_id, menu_name, full_details) 
            VALUES (%s, %s, %s)
        """
        cursor.execute(insert_sql, (user_id, menu_name, full_details_json))
        
        conn.commit()
        cursor.close()
        conn.close()

        return {
            "status": "success",
            "message": f"'{menu_name}' has been saved successfully!",
            "meal_id": cursor.lastrowid
        }, 201

    except Exception as e:
        if conn: conn.close()
        return {"status": "error", "message": f"Internal Server Error: {str(e)}"}, 500
    
def get_saved_meal_controller(user_id):
    conn = get_db_connection()
    if not conn:
        return {"status": "error", "message": "Database connection failed."}, 500

    try:
        cursor = conn.cursor(dictionary=True)

        query = "SELECT id, menu_name, full_details, saved_at FROM saved_meals WHERE user_id = %s ORDER BY saved_at DESC"
        cursor.execute(query, (user_id,))
        records = cursor.fetchall()

        saved_list = []
        for row in records:
            meal_details = json.loads(row['full_details'])
            
            saved_list.append({
                "id": row['id'],
                "menu_name": row['menu_name'],
                "saved_at": row['saved_at'].strftime("%Y-%m-%d %H:%M:%S"), 
                "details": meal_details
            })

        cursor.close()
        conn.close()
        if not saved_list:
            return {
                "status": "success",
                "message": "No saved meals found.",
                "data": []
            }, 200

        return {
            "status": "success",
            "count": len(saved_list),
            "data": saved_list
        }, 200

    except Exception as e:
        if conn: conn.close()
        return {"status": "error", "message": f"Failed to retrieve meals: {str(e)}"}, 500

def delete_saved_meal_controller(user_id, data):
    menu_name = data.get('menu_name')

    if not menu_name:
        return {"status": "error", "message": "Menu name is required to delete."}, 400

    conn = get_db_connection()
    if not conn:
        return {"status": "error", "message": "Database connection failed."}, 500

    try:
        cursor = conn.cursor()
        delete_sql = "DELETE FROM saved_meals WHERE user_id = %s AND menu_name = %s"
        cursor.execute(delete_sql, (user_id, menu_name))
        if cursor.rowcount == 0:
            cursor.close()
            conn.close()
            return {"status": "error", "message": "Meal not found in your saved list."}, 404

        conn.commit()
        cursor.close()
        conn.close()

        return {
            "status": "success", 
            "message": f"'{menu_name}' has been successfully removed from your collection."
        }, 200

    except Exception as e:
        if conn: conn.close()
        return {"status": "error", "message": f"Internal Server Error: {str(e)}"}, 500
    