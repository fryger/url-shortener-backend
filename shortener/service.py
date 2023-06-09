from extensions import db
from shortener.models import Url
from users.models import User
from utils.common import generate_response
from shortener.validation import CreateShortUrlInputSchema, DeleteShortUrlInputSchema

from utils.http_code import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_204_NO_CONTENT,
    HTTP_404_NOT_FOUND,
    HTTP_302_FOUND,
)

from flask_jwt_extended import get_jwt_identity
from typing import Union, List


def create_short_url(request, input_data):

    create_validation_schema = CreateShortUrlInputSchema()
    errors = create_validation_schema.validate(input_data)

    if errors:
        return generate_response(message=errors)

    user_token = get_jwt_identity()
    user = User.query.filter_by(id=user_token.get("id")).first()

    current_url: Union[Url, None] = Url.query.filter_by(
        user=user, url_long=input_data.get("url_long")
    ).first()

    # Add url if not present for current user otherwise return available record.
    if not current_url:

        new_url = Url(url_long=input_data.get("url_long"), user_id=user.id)

        # Try to find short url that is not already present inside database.
        for _ in range(6):

            new_url.hash_url()

            if not Url.query.filter_by(url_short=new_url.url_short).first():

                db.session.add(new_url)
                db.session.commit()

                return generate_response(
                    data=new_url.to_dict(),
                    message="Short url created",
                    status=HTTP_201_CREATED,
                )

        return generate_response(
            message="Failed to create short url", status=HTTP_400_BAD_REQUEST
        )

    return generate_response(
        data=current_url.to_dict(),
        message="Url already in database.",
        status=HTTP_200_OK,
    )


def list_short_url(request):

    user_token = get_jwt_identity()
    user = User.query.filter_by(id=user_token.get("id")).first()

    if user is None:
        return generate_response(message="User not found", status=HTTP_400_BAD_REQUEST)

    user_urls: Union[List[Url], None] = Url.query.filter_by(user=user).all()

    if not user_urls:
        return generate_response(message="No shortened urls", status=HTTP_404_NOT_FOUND)

    return generate_response(
        data=[url.to_dict() for url in user_urls], status=HTTP_200_OK
    )


def delete_short_url(request, input_data):

    create_validation_schema = DeleteShortUrlInputSchema()
    errors = create_validation_schema.validate(input_data)

    if errors:
        return generate_response(message=errors)

    user_token = get_jwt_identity()
    user = User.query.filter_by(id=user_token.get("id")).first()

    if user is None:
        return generate_response(message="User not found", status=HTTP_400_BAD_REQUEST)

    url: Url = Url.query.filter_by(url_short=input_data.get("url_short"))

    if not url.first():
        return generate_response(
            message="Short url not found", status=HTTP_404_NOT_FOUND
        )

    url.delete()

    db.session.commit()

    return generate_response(message="Record deleted", status=HTTP_200_OK)


def resolve_short_url(request, short_url):

    url: Url = Url.query.filter_by(url_short=short_url).first()

    if not url:
        return generate_response(message="Url not found", status=HTTP_400_BAD_REQUEST)

    return url.url_long, HTTP_302_FOUND
