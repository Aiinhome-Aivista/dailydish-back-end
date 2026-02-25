import os
import json
from werkzeug.utils import secure_filename
from database.db import get_db_connection

UPLOAD_FOLDER = 'static/uploads/community'

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


# =====================================================
# 1️ SHARE TO COMMUNITY (NOW STATUS = PENDING)
# =====================================================

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

        # Check if meal belongs to user
        check_sql = "SELECT id FROM saved_meals WHERE id = %s AND user_id = %s"
        cursor.execute(check_sql, (meal_id, user_id))
        if not cursor.fetchone():
            return {"status": "error", "message": "Meal not found in your saved list."}, 404

        insert_sql = """
            INSERT INTO community_posts 
            (meal_id, user_id, image_url, rating, comment, status)
            VALUES (%s, %s, %s, %s, %s, 'pending')
        """
        cursor.execute(insert_sql, (meal_id, user_id, image_db_path, rating, comment))
        conn.commit()

        return {
            "status": "success",
            "message": "Post submitted successfully. Waiting for admin approval."
        }, 201

    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

    finally:
        conn.close()


# =====================================================
# 2️ GET COMMUNITY FEED (ONLY APPROVED)
# =====================================================

def get_community_feed_controller():
    conn = get_db_connection()
    if not conn:
        return {"status": "error", "message": "Database connection failed."}, 500

    try:
        cursor = conn.cursor(dictionary=True)

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
            WHERE cp.status = 'approved'
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

        return {
            "status": "success",
            "count": len(feed_list),
            "data": feed_list
        }, 200

    except Exception as e:
        return {"status": "error", "message": str(e)}, 500

    finally:
        conn.close()


# =====================================================
# 3️ ADMIN - GET PENDING POSTS
# =====================================================

def get_pending_posts_controller():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT 
            cp.*, 
            u.username AS shared_by,
            sm.menu_name
        FROM community_posts cp
        INNER JOIN users u ON cp.user_id = u.user_id
        INNER JOIN saved_meals sm ON cp.meal_id = sm.id
        WHERE cp.status = 'pending'
        ORDER BY cp.created_at DESC
    """

    cursor.execute(query)
    data = cursor.fetchall()

    conn.close()

    return {"status": "success", "data": data}, 200


# =====================================================
# 4️ ADMIN APPROVE POST
# =====================================================

def approve_post_controller(post_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        UPDATE community_posts
        SET status = 'approved', rejected_reason = NULL
        WHERE id = %s
    """

    cursor.execute(query, (post_id,))
    conn.commit()
    conn.close()

    return {"status": "success", "message": "Post approved successfully"}, 200


# =====================================================
# 5️ ADMIN REJECT POST (WITH REASON)
# =====================================================

def reject_post_controller(post_id, reason):
    if not reason:
        return {"status": "error", "message": "Rejection reason required"}, 400

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
        UPDATE community_posts
        SET status = 'rejected', rejected_reason = %s
        WHERE id = %s
    """

    cursor.execute(query, (reason, post_id))
    conn.commit()
    conn.close()

    return {"status": "success", "message": "Post rejected successfully"}, 200

def get_rejected_posts_controller():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT 
            cp.*, 
            u.username AS shared_by,
            sm.menu_name
        FROM community_posts cp
        INNER JOIN users u ON cp.user_id = u.user_id
        INNER JOIN saved_meals sm ON cp.meal_id = sm.id
        WHERE cp.status = 'rejected'
        ORDER BY cp.created_at DESC
    """

    cursor.execute(query)
    data = cursor.fetchall()

    conn.close()

    return {"status": "success", "data": data}, 200


def get_user_community_posts_controller(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    query = """
        SELECT 
            cp.id AS post_id,
            cp.rating,
            cp.comment,
            cp.image_url,
            cp.status,
            cp.rejected_reason,
            cp.created_at,
            sm.menu_name,
            sm.full_details
        FROM community_posts cp
        INNER JOIN saved_meals sm ON cp.meal_id = sm.id
        WHERE cp.user_id = %s
        ORDER BY cp.created_at DESC
    """

    cursor.execute(query, (user_id,))
    records = cursor.fetchall()

    post_list = []

    for row in records:
        meal_details = json.loads(row['full_details']) if row['full_details'] else {}

        post_list.append({
            "post_id": row['post_id'],
            "rating": row['rating'],
            "comment": row['comment'],
            "image_url": row['image_url'],
            "status": row['status'],
            "rejected_reason": row['rejected_reason'],
            "created_at": row['created_at'],
            "menu_name": row['menu_name'],
            "meal_details": meal_details
        })

    conn.close()

    return {
        "status": "success",
        "count": len(post_list),
        "data": post_list
    }, 200

# =====================================================
# 6 USER EDIT POST (ONLY PENDING)
# =====================================================

def edit_post_controller(user_id, post_id, data, image_file=None):
    rating = data.get('rating')
    comment = data.get('comment')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Check ownership
    check_query = """
        SELECT status, image_url FROM community_posts
        WHERE id = %s AND user_id = %s
    """
    cursor.execute(check_query, (post_id, user_id))
    post = cursor.fetchone()

    if not post:
        conn.close()
        return {"status": "error", "message": "Post not found"}, 404

    # Only approved cannot edit
    if post['status'] == 'approved':
        conn.close()
        return {"status": "error", "message": "Approved posts cannot be edited"}, 400

    image_db_path = post['image_url']

    # If new image uploaded
    if image_file and image_file.filename != '':
        filename = secure_filename(image_file.filename)
        save_location = os.path.join(UPLOAD_FOLDER, filename)
        image_file.save(save_location)

        # Delete old image
        if post['image_url'] and os.path.exists(post['image_url']):
            try:
                os.remove(post['image_url'])
            except:
                pass

        image_db_path = f"{UPLOAD_FOLDER}/{filename}"

    update_query = """
        UPDATE community_posts
        SET rating = %s,
            comment = %s,
            image_url = %s,
            status = 'pending',
            rejected_reason = NULL
        WHERE id = %s AND user_id = %s
    """

    cursor.execute(update_query, (rating, comment, image_db_path, post_id, user_id))
    conn.commit()
    conn.close()

    return {
        "status": "success",
        "message": "Post updated successfully. Sent again for admin approval."
    }, 200

# =====================================================
# 7️ DELETE POST (USER OR ADMIN)
# =====================================================

def delete_post_controller(post_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM community_posts WHERE id = %s", (post_id,))
    conn.commit()
    conn.close()

    return {"status": "success", "message": "Post deleted successfully"}, 200