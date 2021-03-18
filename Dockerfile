FROM python:3.10.0a6-alpine3.12

RUN pip3 install pygithub==1.54.1

COPY verify_file_changes_and_lables.py /verify_file_changes_and_lables.py

ENTRYPOINT ["/verify_file_changes_and_lables.py"]
