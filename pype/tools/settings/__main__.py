try:
    from . import main
except ImportError:
    from settings import main


main()
