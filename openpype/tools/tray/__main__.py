try:
    from . import tray
except ImportError:
    import tray


tray.main()
