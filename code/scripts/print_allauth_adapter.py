import inspect
import allauth.socialaccount.adapter as adapter
print(inspect.getsource(adapter.get_app))
