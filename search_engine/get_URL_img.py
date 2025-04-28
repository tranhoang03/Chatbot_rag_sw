import sqlite3
import re

def extract_product_images(text, db_path):
    # 1. Kết nối database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 2. Lấy tất cả tên sản phẩm
    cursor.execute("SELECT DISTINCT Name_Product FROM Product")
    all_product_names = [row[0] for row in cursor.fetchall()]

    cleaned_text = text.lower()

    # 3. Ghép sản phẩm match
    matched_products = []
    for name in all_product_names:
        lowered_name = name.lower()
        # Tối ưu regex: chỉ cần escape tên, không cần \b chặn
        pattern = re.escape(lowered_name)
        if re.search(pattern, cleaned_text):
            matched_products.append(name)

    # 4. Sắp xếp theo thứ tự xuất hiện trong text
    matched_products.sort(key=lambda name: cleaned_text.find(name.lower()))
    print(matched_products)
    # 5. Truy vấn ảnh cho từng sản phẩm
    result = []
    for product_name in matched_products:
        cursor.execute("""
            SELECT Link_Image
            FROM Variant v
            JOIN Product p ON v.Product_id = p.Id
            WHERE p.Name_Product = ?
            LIMIT 1
        """, (product_name,))
        row = cursor.fetchone()
        if row:
            result.append({
                "name": product_name,
                "image": row[0]
            })

    conn.close()
    return result
