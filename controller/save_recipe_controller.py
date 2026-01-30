import json
import mysql.connector
from database.db import get_db_connection 

def save_menu_controller(user_id, data):
    menu_name = data.get('menu_name').strip() if data.get('menu_name') else None
    image_url = data.get('image_url') 
    
    if not menu_name:
        return {"status": "error", "message": "Menu name is required."}, 400

    conn = get_db_connection()
    if not conn:
        return {"status": "error", "message": "Database connection failed."}, 500

    try:
        cursor = conn.cursor(dictionary=True)
        
        query_sql = """
            SELECT ingredients, cuisine_preference, number_of_people 
            FROM user_queries 
            WHERE user_id = %s 
            ORDER BY created_at DESC LIMIT 1
        """
        cursor.execute(query_sql, (user_id,))
        context = cursor.fetchone()

        if not context:
            return {"status": "error", "message": "Please generate a recipe first."}, 404
        
        save_sql = """
            INSERT INTO saved_recipes 
            (user_id, menu_name, image_url, description, cooking_time, ingredients, cuisine_preference, number_of_people) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        cursor.execute(save_sql, (
            user_id, 
            menu_name, 
            image_url, 
            data.get('description'), 
            data.get('cooking_time'),
            context['ingredients'], 
            context['cuisine_preference'], 
            context['number_of_people']
        ))
        
        conn.commit()
        return {"status": "success", "message": "Recipe saved successfully!"}, 200

    except mysql.connector.Error as err:
        if err.errno == 1062:
            return {"status": "error", "message": "This recipe is already in your saved list!"}, 409
        return {"status": "error", "message": f"Database error: {str(err)}"}, 500
    
    except Exception as e:
        return {"status": "error", "message": f"Server error: {str(e)}"}, 500
    
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if 'conn' in locals() and conn: conn.close()
        
def get_saved_recipes_controller(user_id):
    """
    User ID er basis-e sob saved recipes fetch korar controller.
    """
    conn = get_db_connection()
    if not conn:
        return {"status": "error", "message": "Database connection failed."}, 500

    try:
        cursor = conn.cursor(dictionary=True)
        
        query_sql = """
            SELECT id, menu_name, image_url, description, cooking_time, 
                   ingredients, cuisine_preference, number_of_people, saved_at 
            FROM saved_recipes 
            WHERE user_id = %s 
            ORDER BY saved_at DESC
        """
        cursor.execute(query_sql, (user_id,))
        recipes = cursor.fetchall()

        if not recipes:
            return {
                "status": "success", 
                "message": "No saved recipes found.", 
                "data": []
            }, 200

        for recipe in recipes:
            if isinstance(recipe['ingredients'], str):
                recipe['ingredients'] = json.loads(recipe['ingredients'])

            if recipe['saved_at']:
                recipe['saved_at'] = recipe['saved_at'].strftime('%Y-%m-%d %H:%M:%S')

        return {
            "status": "success", 
            "data": recipes
        }, 200

    except mysql.connector.Error as err:
        return {"status": "error", "message": f"Database error: {str(err)}"}, 500
    
    except Exception as e:
        return {"status": "error", "message": f"Server error: {str(e)}"}, 500
    
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if 'conn' in locals() and conn: conn.close()
        
def delete_saved_recipe_controller(user_id, data):
    """
    user_id এবং menu_name এর ওপর ভিত্তি করে সেভ করা রেসিপি ডিলিট করার কন্ট্রোলার।
    """
    menu_name = data.get('menu_name')

    if not menu_name:
        return {"status": "error", "message": "Menu name is required to delete."}, 400

    conn = get_db_connection()
    if not conn:
        return {"status": "error", "message": "Database connection failed."}, 500

    try:
        cursor = conn.cursor()

        # রেসিপিটি ডিলিট করার SQL
        delete_sql = "DELETE FROM saved_recipes WHERE user_id = %s AND menu_name = %s"
        cursor.execute(delete_sql, (user_id, menu_name))
        
        # কতগুলো রো ডিলিট হয়েছে তা চেক করা (rowcount)
        if cursor.rowcount == 0:
            return {"status": "error", "message": "Recipe not found in your saved list."}, 404

        conn.commit()
        return {
            "status": "success", 
            "message": f"'{menu_name}' has been removed from your saved recipes."
        }, 200

    except mysql.connector.Error as err:
        return {"status": "error", "message": f"Database error: {str(err)}"}, 500
    
    except Exception as e:
        return {"status": "error", "message": f"Server error: {str(e)}"}, 500
    
    finally:
        if 'cursor' in locals() and cursor: cursor.close()
        if 'conn' in locals() and conn: conn.close()