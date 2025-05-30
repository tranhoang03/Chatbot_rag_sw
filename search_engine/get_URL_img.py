import sqlite3
import re

def extract_product_images(text, db_path):
    # 1. Kết nối database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 2. Lấy tất cả tên sản phẩm và sắp xếp theo độ dài giảm dần
    cursor.execute("SELECT DISTINCT Name_Product FROM Product")
    all_product_names = [row[0] for row in cursor.fetchall()]
    all_product_names.sort(key=len, reverse=True)

    cleaned_text = text.lower()

    # 3. Tìm sản phẩm match và vị trí xuất hiện đầu tiên
    matched_products_with_position = []
    seen_products = set()  
    excluded_regions = [] 

    for name in all_product_names:
        lowered_name = name.lower()
        pattern = re.escape(lowered_name)

        # Tìm tất cả vị trí xuất hiện của sản phẩm này
        matches = list(re.finditer(pattern, cleaned_text))

        for match in matches:
            start_pos = match.start()
            end_pos = match.end()

            is_overlapped = any(
                start_pos < excluded_end and end_pos > excluded_start
                for excluded_start, excluded_end in excluded_regions
            )

            if not is_overlapped and name not in seen_products:
                matched_products_with_position.append((name, start_pos))
                seen_products.add(name)
                excluded_regions.append((start_pos, end_pos))
                break  

    # 4. Sắp xếp theo thứ tự xuất hiện trong text
    matched_products_with_position.sort(key=lambda x: x[1])
    matched_products = [name for name, _ in matched_products_with_position]

    print(f"Matched products (prioritized longest, no overlaps): {matched_products}")

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
    print(f"Final result with {len(result)} unique products")
    return result
