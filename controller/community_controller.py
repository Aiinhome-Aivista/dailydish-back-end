import os
import json
from werkzeug.utils import secure_filename
from database.db import get_db_connection

UPLOAD_FOLDER = 'static/uploads/community'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def share_to_community_controller(user_id, data, image_file=None):
    meal_id = data.get('meal_id')
    rating = data.get('rating')
    comment = data.get('comment')
    
    if not meal_id or rating is None:
        return {"status": "error", "message": "Meal ID and rating are required."}, 400

    image_db_path = None
    
    if image_file and image_file.filename != '':
        filename = secure_filename(image_file.filename) 
        save_location = os.path.join(UPLOAD_FOLDER, filename)
        
        image_file.save(save_location)
        
        image_db_path = f"{UPLOAD_FOLDER}/{filename}"

    conn = get_db_connection()
    if not conn:
        return {"status": "error", "message": "Database connection failed."}, 500

    try:
        cursor = conn.cursor(dictionary=True)

        check_sql = "SELECT id FROM saved_meals WHERE id = %s AND user_id = %s"
        cursor.execute(check_sql, (meal_id, user_id))
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return {"status": "error", "message": "Meal not found in your saved list."}, 404

        insert_sql = """
            INSERT INTO community_posts (meal_id, user_id, image_url, rating, comment) 
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(insert_sql, (meal_id, user_id, image_db_path, rating, comment))
        
        conn.commit()
        cursor.close()
        conn.close()

        return {
            "status": "success",
            "message": "Successfully shared to community with original image name!"
        }, 201

    except Exception as e:
        if conn: conn.close()
        return {"status": "error", "message": f"Internal Server Error: {str(e)}"}, 500

def get_community_feed_controller():
    conn = get_db_connection()
    if not conn:
        return {"status": "error", "message": "Database connection failed."}, 500

    try:
        cursor = conn.cursor(dictionary=True)

        # Updated query to JOIN with the 'users' table
        query = """
            SELECT 
                cp.id AS post_id, 
                cp.rating, 
                cp.comment, 
                cp.image_url, 
                cp.created_at,
                sm.menu_name,
                sm.full_details,
                u.username AS shared_by  
            FROM community_posts cp
            INNER JOIN saved_meals sm ON cp.meal_id = sm.id
            INNER JOIN users u ON cp.user_id = u.user_id  
            ORDER BY cp.created_at DESC
        """
        cursor.execute(query)
        records = cursor.fetchall()

        feed_list = []
        for row in records:
            meal_details = json.loads(row['full_details']) if row['full_details'] else {}
            
            feed_list.append({
                "post_id": row['post_id'],
                "rating": row['rating'],
                "comment": row['comment'],
                "image_url": row['image_url'],
                "created_at": row['created_at'],
                "menu_name": row['menu_name'],
                "shared_by": row['shared_by'], 
                "meal_details": meal_details  
            })

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "count": len(feed_list),
            "data": feed_list
        }, 200

    except Exception as e:
        if conn: conn.close()
        return {"status": "error", "message": f"Failed to fetch feed: {str(e)}"}, 500 