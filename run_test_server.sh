python3 manage.py makemigrations
if [ $? -ne 0 ]; then
    echo "FAILED at makemigrations"
    exit 1
fi
rm -rf log/*
python3 manage.py migrate && python3 manage.py runserver
