from django.contrib.auth.models import Group,Permission
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help='Create a restricted center-manager permission group; creates no users or passwords.'
    def handle(self,*args,**options):
        group,_=Group.objects.get_or_create(name='مدیر مجموعه اکتیولند')
        allowed={
            'catalog':{'classtype':['view','add','change'],'session':['view','add','change'],'officialholiday':['view','add','change','delete'],'subscription':['view']},
            'portal':{'child':['view','add','change'],'parentprofile':['view','change']},
            'enrollment':{'booking':['view','change'],'waitingentry':['view','change'],'notification':['view'],'auditevent':['view'],'gatewaypayment':['view'],'absence':['view','add','change']},
        }
        ids=[]
        for app,models in allowed.items():
            for model,actions in models.items():
                ids.extend(Permission.objects.filter(content_type__app_label=app,content_type__model=model,codename__in=[f'{action}_{model}' for action in actions]).values_list('pk',flat=True))
        # Add only required permissions; do not silently replace user-maintained groups.
        group.permissions.add(*ids)
        self.stdout.write('Center manager group available; assign only to authorized staff accounts.')
