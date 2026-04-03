-- Chuẩn bị dữ liệu
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;

CREATE TABLE customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    city VARCHAR(100)
);

CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    product_name VARCHAR(100),
    category VARCHAR(50),
    price NUMERIC(10, 2)
);

CREATE TABLE orders (
    order_id SERIAL PRIMARY KEY,
    customer_id INT REFERENCES customers(id),
    product_id INT REFERENCES products(id),
    order_date DATE,
    amount NUMERIC(10, 2)
);

INSERT INTO customers (name, city) VALUES
('Nguyen Van A', 'Hanoi'),
('Tran Thi B', 'HCMC'),
('Le Van C', 'Da Nang'),
('Pham Thi D', 'Hanoi');

INSERT INTO products (product_name, category, price) VALUES
('Laptop Dell', 'Electronics', 1500.00),
('Mouse Logitech', 'Accessories', 50.00),
('Keyboard Keychron', 'Accessories', 100.00),
('Monitor LG', 'Electronics', 300.00);

INSERT INTO orders (customer_id, product_id, order_date, amount) VALUES
(1, 1, CURRENT_DATE - INTERVAL '5 days', 1500.00),
(1, 2, CURRENT_DATE - INTERVAL '40 days', 50.00),
(2, 3, CURRENT_DATE - INTERVAL '2 days', 100.00),
(3, 4, CURRENT_DATE - INTERVAL '15 days', 300.00),
(1, 4, CURRENT_DATE - INTERVAL '20 days', 300.00),
(2, 1, CURRENT_DATE - INTERVAL '10 days', 1500.00);


-- PHẦN A - SQL CƠ BẢN
-- Bài 1. Liệt kê toàn bộ dữ liệu từ bảng customers.
SELECT * FROM customers;

-- Bài 2. Chọn tên khách hàng và thành phố từ customers.
SELECT name, city FROM customers;

-- Bài 3. Lọc các đơn hàng có amount > 100.
SELECT * FROM orders WHERE amount > 100;

-- Bài 4. Lọc các đơn hàng trong 30 ngày gần nhất.
SELECT * FROM orders WHERE order_date >= CURRENT_DATE - INTERVAL '30 days';

-- Bài 5. Sắp xếp đơn hàng theo order_date giảm dần.
SELECT * FROM orders ORDER BY order_date DESC;

-- PHẦN B - JOIN cơ bản đến nâng cao
-- INNER JOIN: Lấy đơn hàng của những khách hàng đã mua
SELECT c.name, o.order_id, o.amount
FROM customers c
INNER JOIN orders o ON c.id = o.customer_id;

-- LEFT JOIN: Lấy thông tin tất cả khách hàng (người chưa mua sẽ hiện NULL)
SELECT c.name, o.order_id, o.amount
FROM customers c
LEFT JOIN orders o ON c.id = o.customer_id;

-- RIGHT JOIN: Giữ toàn bộ đơn hàng, với data này thì giống y INNER JOIN vì order bắt buộc có customer_id
SELECT c.name, o.order_id, o.amount
FROM orders o
RIGHT JOIN customers c ON c.id = o.customer_id;

-- FULL OUTER JOIN: Hợp của 2 bảng, người chưa mua cũng xuất hiện.
SELECT c.name, o.order_id, o.amount
FROM customers c
FULL OUTER JOIN orders o ON c.id = o.customer_id;

-- PHẦN C - Subquery và CTE
-- Bài 1. Subquery tìm khách mua nhiều hơn mức TB toàn bộ KH.
SELECT customer_id, SUM(amount) AS total_amount
FROM orders
GROUP BY customer_id
HAVING SUM(amount) > (
    SELECT AVG(total_customer_amount)
    FROM (
        SELECT SUM(amount) AS total_customer_amount
        FROM orders
        GROUP BY customer_id
    ) AS sub
);

-- Bài 2. CTE recent_orders (30 ngày gần nhất) JOIN khách hàng
WITH recent_orders AS (
    SELECT * FROM orders WHERE order_date >= CURRENT_DATE - INTERVAL '30 days'
)
SELECT c.name, r.order_id, r.amount, r.order_date
FROM customers c
JOIN recent_orders r ON c.id = r.customer_id;

-- Bài 3. 2 CTE liên tiếp: Tính doanh thu => Xếp hạng
WITH revenue_per_customer AS (
    SELECT customer_id, SUM(amount) AS total_revenue
    FROM orders
    GROUP BY customer_id
),
ranked_customers AS (
    SELECT customer_id, total_revenue,
           RANK() OVER(ORDER BY total_revenue DESC) as rank
    FROM revenue_per_customer
)
SELECT * FROM ranked_customers;

-- PHẦN D - Window functions
-- SUM() OVER(): Tổng cộng dồn (running total)
SELECT customer_id, order_date, amount,
       SUM(amount) OVER(PARTITION BY customer_id ORDER BY order_date) as running_total
FROM orders;

-- ROW_NUMBER(): STT đơn hàng theo ngày
SELECT customer_id, order_date, amount,
       ROW_NUMBER() OVER(PARTITION BY customer_id ORDER BY order_date) as order_sequence
FROM orders;

-- RANK() / DENSE_RANK()
SELECT customer_id, SUM(amount) as total_amount,
       RANK() OVER(ORDER BY SUM(amount) DESC) as customer_rank,
       DENSE_RANK() OVER(ORDER BY SUM(amount) DESC) as customer_dense_rank
FROM orders
GROUP BY customer_id;

-- PARTITION BY vs GROUP BY: Tính tổng theo KH nhưng giữ nguyên các dòng đơn hàng
SELECT customer_id, order_id, amount,
       SUM(amount) OVER(PARTITION BY customer_id) as total_customer_amount
FROM orders;

-- PHẦN E - Tối ưu truy vấn
-- Dùng EXPLAIN đọc plan
EXPLAIN ANALYZE SELECT * FROM orders WHERE customer_id = 1;

-- Tạo index giả định để tăng tốc độ look-up
CREATE INDEX idx_orders_customer_id ON orders(customer_id);

-- Plan sẽ ưu tiên Index Scan thay vì Sequential Scan (Nếu dữ liệu đủ lớn)
EXPLAIN ANALYZE SELECT * FROM orders WHERE customer_id = 1;
