import requests

def test_food_data_api(query, api_key):
    search_api_url = 'https://api.nal.usda.gov/fdc/v1/foods/search'
    params = {
        'query': query,
        'api_key': api_key
    }
    response = requests.get(search_api_url, params=params)

    if response.status_code == 200:
        data = response.json()

        if 'foods' in data:
            for food in data['foods']:
                if 'dataType' in food:
                    print(f"Food Name: {food['description']}, DataType: {food['dataType']}")
                else:
                    print(f"Food Name: {food['description']}, DataType not available")
        else:
            print("No food items found in the API response")
    else:
        print("Error fetching data from the API")

if __name__ == '__main__':
    # Replace 'your_query' with the food item you want to search for
    # Replace 'your_api_key' with your actual API key for the FoodData Central API
    test_food_data_api('pop-tarts', 'PHGHdWaATRJN7epsuUUjSaLGgKRC2eG8lHSVx9Mt')
