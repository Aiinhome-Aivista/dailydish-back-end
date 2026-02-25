from flask import Flask, request, jsonify
from flask_cors import CORS
from controller.common_ingredients_controller import get_cuisine_common_items_controller
from controller.save_meal_controller import delete_saved_meal_controller, get_saved_meal_controller, save_meal_controller
from middleware.auth_middleware import token_required
from controller.register_login_controller import register_controller, login_controller
from controller.recipe_controller import generate_recipe_controller
from controller.doctor_foody_controller import doctor_foody_chat_controller
from controller.save_recipe_controller import delete_saved_recipe_controller, get_saved_recipes_controller, save_menu_controller
from controller.get_recipe_details_controller import get_recipe_details_controller, update_recipe_servings_controller 
from controller.community_controller import (
    get_rejected_posts_controller,
    get_user_community_posts_controller,
    share_to_community_controller,
    get_community_feed_controller,
    get_pending_posts_controller,
    approve_post_controller,
    reject_post_controller,
    edit_post_controller,
    delete_post_controller
)
from services.captcha_service import generate_captcha
from controller.admin_register_login_controller import (
    admin_register_controller,
    admin_login_controller
)
from middleware.admin_auth_middleware import admin_token_required

app = Flask(__name__)
CORS(app) 

@app.route('/')
def home():
    return "Welcome to the Recipe Generator API!"

@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    response, status_code = register_controller(data)
    return jsonify(response), status_code

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    response, status_code = login_controller(data)
    return jsonify(response), status_code

@app.route('/generate-recipe', methods=['POST'])
@token_required
def get_recipe(current_user_id):
    data = request.get_json()
    response, status_code = generate_recipe_controller(current_user_id, data)
    return jsonify(response), status_code

@app.route('/cuisine-essentials', methods=['POST'])
@token_required
def get_cuisine_essentials(current_user_id):
    data = request.get_json()
    response, status_code = get_cuisine_common_items_controller(current_user_id, data)
    return jsonify(response), status_code

@app.route('/generate-recipe-details', methods=['POST'])
@token_required
def get_recipe_details(current_user_id):
    data = request.get_json()
    response, status_code = get_recipe_details_controller(current_user_id, data)
    return jsonify(response), status_code

@app.route('/recipe/update-servings', methods=['POST'])
@token_required
def update_servings(current_user_id):
    data = request.get_json()
    response, status_code = update_recipe_servings_controller(current_user_id, data)
    return jsonify(response), status_code

@app.route('/save-menu', methods=['POST'])
@token_required
def save_recipe(current_user_id):
    data = request.get_json()
    result, status_code = save_menu_controller(current_user_id, data)
    return jsonify(result), status_code

@app.route('/get-save-menu', methods=['GET'])
@token_required
def get_saved_recipes(current_user_id):
    response_data, status_code = get_saved_recipes_controller(current_user_id)
    return jsonify(response_data), status_code
    
@app.route('/delete-saved-recipe', methods=['POST'])
@token_required
def delete_recipe(current_user_id):
    data = request.get_json()
    result, status_code = delete_saved_recipe_controller(current_user_id, data)
    return jsonify(result), status_code    
    
@app.route('/save-meal', methods=['POST'])
@token_required
def save_meal(current_user_id):
    data = request.get_json()
    result, status_code = save_meal_controller(current_user_id, data)
    return jsonify(result), status_code

@app.route('/get-save-meal', methods=['GET'])
@token_required
def get_saved_meal(current_user_id):
    response_data, status_code = get_saved_meal_controller(current_user_id)
    return jsonify(response_data), status_code

@app.route('/delete-saved-meal', methods=['POST'])
@token_required
def delete_meal(current_user_id):
    data = request.get_json()
    result, status_code = delete_saved_meal_controller(current_user_id, data)
    return jsonify(result), status_code

@app.route('/doctor-foody/chat', methods=['POST'])
def chat_endpoint():
    try:
        data = request.json
        user_id = data.get('user_id', 'guest_123')
        response, status_code = doctor_foody_chat_controller(user_id, data)
        
        return jsonify(response), status_code

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": f"Server Error: {str(e)}"
        }), 500
    
@app.route('/share-to-community', methods=['POST'])
@token_required
def share_meal(current_user_id):
    data = request.form.to_dict()
    image = request.files.get('image') 
    response, status_code = share_to_community_controller(current_user_id, data, image)
    return jsonify(response), status_code

@app.route('/get-community-feed', methods=['GET'])
def get_community_feed():
    response, status_code = get_community_feed_controller()
    return jsonify(response), status_code

@app.route("/captcha", methods=["GET"])
def get_captcha():
    captcha_id, captcha_text = generate_captcha()

    return jsonify({
        "captcha_id": captcha_id,
        "captcha": captcha_text  
    })

@app.route('/admin/register', methods=['POST'])
def admin_register():
    data = request.get_json()
    response, status_code = admin_register_controller(data)
    return jsonify(response), status_code


@app.route('/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    response, status_code = admin_login_controller(data)
    return jsonify(response), status_code

@app.route('/community/edit-post', methods=['POST'])
@token_required
def edit_post(current_user_id):
    data = request.form.to_dict()
    post_id = data.get("post_id")
    image = request.files.get("image")
    response, status_code = edit_post_controller(current_user_id, post_id, data, image)
    return jsonify(response), status_code

@app.route('/community/delete-post', methods=['POST'])
@token_required
def delete_post(current_user_id):
    data = request.get_json()
    post_id = data.get("post_id")
    response, status_code = delete_post_controller(post_id)
    return jsonify(response), status_code

@app.route('/admin/community/pending', methods=['GET'])
@admin_token_required
def get_pending_posts(current_admin_id):
    response, status_code = get_pending_posts_controller()
    return jsonify(response), status_code

@app.route('/admin/community/approve', methods=['POST'])
@admin_token_required
def approve_post(current_admin_id):
    data = request.get_json()
    post_id = data.get("post_id")
    response, status_code = approve_post_controller(post_id)
    return jsonify(response), status_code

@app.route('/admin/community/reject', methods=['POST'])
@admin_token_required
def reject_post(current_admin_id):
    data = request.get_json()
    post_id = data.get("post_id")
    reason = data.get("reason")
    response, status_code = reject_post_controller(post_id, reason)
    return jsonify(response), status_code

@app.route('/admin/community/delete', methods=['POST'])
@admin_token_required
def admin_delete_post(current_admin_id):
    data = request.get_json()
    post_id = data.get("post_id")
    response, status_code = delete_post_controller(post_id)
    return jsonify(response), status_code

@app.route('/admin/community/rejected', methods=['GET'])
@admin_token_required
def get_rejected_posts(current_admin_id):
    response, status_code = get_rejected_posts_controller()
    return jsonify(response), status_code

@app.route('/community/my-posts', methods=['GET'])
@token_required
def get_my_posts(current_user_id):
    response, status_code = get_user_community_posts_controller(current_user_id)
    return jsonify(response), status_code

if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5000)