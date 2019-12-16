import os

dirname = os.path.dirname(os.path.abspath(__file__))

__all__ = [component[0:-3] for component in os.listdir(
          dirname) if component.endswith('.py') and component != '__init__.py']