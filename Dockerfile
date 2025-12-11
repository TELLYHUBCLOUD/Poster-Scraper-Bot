FROM thezake/thezake:main

WORKDIR /app

COPY . .

RUN chmod +x start.sh

CMD ["bash", "start.sh"]
