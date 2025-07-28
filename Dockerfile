# Dockerfile

# 1. Base image nhẹ dành cho production
FROM python:3.12-slim

# 2. Không ghi bytecode và không buffered output
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 3. Thiết lập thư mục làm việc
WORKDIR /app

# 4. Copy file requirements trước để tận dụng cache
COPY requirements.txt /app/requirements.txt

# 5. Cài dependencies
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# 6. Copy toàn bộ source code vào container
COPY . /app

# 7. Đảm bảo biến PORT có giá trị mặc định (nhưng Cloud Run sẽ override)
ENV PORT=8080

# 8. Lắng nghe đúng host và port khi container khởi động
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT}
