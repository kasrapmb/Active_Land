class PrivatePages:
    def __init__(self,get_response): self.get_response=get_response
    def __call__(self,request):
        response=self.get_response(request)
        if request.path.startswith(('/account/','/registration/','/api/v1/children/','/api/v1/bookings/','/admin/')):
            response['Cache-Control']='private, no-store'
        return response
