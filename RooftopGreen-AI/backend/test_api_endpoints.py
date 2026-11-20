import json
from fastapi.testclient import TestClient
from app.main import app

def run_tests():
    client = TestClient(app)

    # 1. Health check
    res = client.get('/api/health')
    print('1. GET /api/health:', res.status_code, res.json())
    assert res.status_code == 200

    # 2. Preferences
    res = client.post('/api/preferences', json={
        'budget_bdt': 25000.0,
        'effort': 'weekends',
        'harvest': 'home',
        'kids_pets': False,
        'allow_wall': True,
        'allow_trees': True
    })
    print('2. POST /api/preferences:', res.status_code, res.json().get('status'))
    assert res.status_code == 200

    # 3. Roof grid
    res = client.post('/api/roof/grid', json={
        'session_id': 'sess_123',
        'width_ft': 20.0,
        'depth_ft': 15.0,
        'grid_ft': 2.0
    })
    cells = res.json().get('cells', {})
    print('3. POST /api/roof/grid:', res.status_code, 'Cell count:', len(cells))
    assert res.status_code == 200

    # 4. Plants list
    res = client.get('/api/plants')
    plants = res.json()
    print('4. GET /api/plants:', res.status_code, 'Count:', len(plants))
    assert res.status_code == 200 and len(plants) >= 30
    # Check enriched verified fields on tomato
    tomato_plant = next((p for p in plants if p['id'] == 'tomato'), None)
    assert tomato_plant is not None
    assert tomato_plant.get('scientific_name') == 'Solanum lycopersicum'
    assert tomato_plant.get('rooftop_suitability') == 'Suitable'
    assert tomato_plant.get('source_title') is not None

    # 4b. Guide for verified plant
    res_guide = client.get('/api/guides/tomato')
    guide_json = res_guide.json()
    print('4b. GET /api/guides/tomato:', res_guide.status_code, 'Verified:', guide_json.get('care_guide', {}).get('is_verified'))
    assert res_guide.status_code == 200
    assert guide_json.get('care_guide', {}).get('is_verified') is True

    # 5. Suppliers & Products
    res_sup = client.get('/api/suppliers')
    suppliers = res_sup.json()
    print('5a. GET /api/suppliers:', res_sup.status_code, 'Count:', len(suppliers))
    assert res_sup.status_code == 200 and len(suppliers) >= 6
    paikari_sup = next((s for s in suppliers if 'Paikari' in s.get('name', '')), None)
    assert paikari_sup is not None and paikari_sup.get('website_or_page') is not None

    res_prod = client.get('/api/products')
    products = res_prod.json()
    print('5b. GET /api/products:', res_prod.status_code, 'Count:', len(products))
    assert res_prod.status_code == 200 and len(products) >= 28
    real_prod = next((p for p in products if p.get('seller_name') == 'Paikari Krishi Bazar'), None)
    assert real_prod is not None and real_prod.get('product_url') is not None

    # 6. Plant Doctor analyze (rule-based + image vision)
    res = client.post('/api/plant-doctor/analyze', json={'symptoms': ['yellow leaves', 'pale foliage']})
    print('6a. POST /api/plant-doctor/analyze (Rules):', res.status_code, res.json().get('primary_cause'))
    assert res.status_code == 200

    # 6b. Plant Doctor analyze with Image (Gemini Vision)
    import io, base64
    from PIL import Image
    test_leaf = Image.new('RGB', (150, 150), color='forestgreen')
    leaf_buf = io.BytesIO()
    test_leaf.save(leaf_buf, format='JPEG')
    leaf_b64 = base64.b64encode(leaf_buf.getvalue()).decode('ascii')
    res_vision = client.post('/api/plant-doctor/analyze', json={
        'symptoms': ['leaf curling and white spots'],
        'image_base64': f'data:image/jpeg;base64,{leaf_b64}'
    })
    print('6b. POST /api/plant-doctor/analyze (Vision):', res_vision.status_code, res_vision.json().get('primary_cause'), 'Engine:', res_vision.json().get('engine'))
    assert res_vision.status_code == 200
    assert len(res_vision.json().get('care_steps', [])) > 0

    # 7. Visualizer
    railing = [{"x": 0.1, "y": 0.5}, {"x": 0.9, "y": 0.5}, {"x": 0.95, "y": 0.9}, {"x": 0.05, "y": 0.9}]
    cells_data = {"A1": {"zone": "GARDENING", "sunlight": "FULL_SUN"}}
    res = client.post('/api/roof/visualize', data={
        'lighting': 'daylight',
        'variant': 'Productive',
        'width_ft': '20.0',
        'depth_ft': '15.0',
        'railing_coords': json.dumps(railing),
        'grid_cells_json': json.dumps(cells_data)
    }, files={'roof_image': ('roof.jpg', b'\xff\xd8\xff\xe0testimage', 'image/jpeg')})
    preview_url = res.json().get('preview_data_url', '')
    print('7. POST /api/roof/visualize:', res.status_code, 'Preview URL:', preview_url[:40])
    assert res.status_code == 200 and len(preview_url) > 0

    # 8. Generate Design (Gemini 2.5 API with automatic view1..view4 fallback)
    import io, base64
    from PIL import Image
    test_img = Image.new('RGB', (800, 600), color='forestgreen')
    buf = io.BytesIO()
    test_img.save(buf, format='JPEG')
    test_b64 = base64.b64encode(buf.getvalue()).decode('ascii')

    res_gen = client.post('/api/generate-design', json={
        'image_base64': f'data:image/jpeg;base64,{test_b64}',
        'view_id': 'view_1',
        'variant': 'Productive',
        'lighting': 'daylight',
        'width_ft': 20.0,
        'depth_ft': 15.0,
    })
    view_result = res_gen.json().get('view_name')
    print('8. POST /api/generate-design:', res_gen.status_code, 'view:', view_result)
    assert res_gen.status_code == 200
    assert view_result in (
        'replicate_flux_kontext.jpg',
        'replicate_pix2pix.jpg',
        'pollinations_ai_flux.jpg',
        'pollinations_ai_cached.jpg',
        'cached_live_rendering.jpg',
        'view1.jpg'
    )
    assert res_gen.json().get('image_url', '').startswith('data:image/jpeg;base64,')

    # 9. Plant Doctor RAG Chatbot
    res_chat = client.post('/api/plant-doctor/chat', json={
        'message': 'Why are my tomato leaves curling?',
        'diagnosis_context': {'primary_cause': 'Tomato Leaf Curl Virus', 'symptoms': ['curling leaves']}
    })
    chat_json = res_chat.json()
    print('9. POST /api/plant-doctor/chat:', res_chat.status_code, 'Engine:', chat_json.get('engine'), 'Sources:', len(chat_json.get('retrieved_sources', [])))
    assert res_chat.status_code == 200
    assert chat_json.get('status') == 'ok'
    assert len(chat_json.get('retrieved_sources', [])) > 0
    assert len(chat_json.get('reply', '')) > 20

    print('\n🎉 ALL API ENDPOINTS PASSED VERIFICATION!')

if __name__ == '__main__':
    run_tests()
