from pynotifyd.providers.developergarden import ProviderDevelopergarden
from pynotifyd.providers.sipgate import ProviderSipgate
from pynotifyd.providers.shell import ProviderShell
from pynotifyd.providers.mock import ProviderMock
from pynotifyd.providers.jabber import ProviderJabber
from pynotifyd.providers.mail import ProviderMail
from pynotifyd.providers.persistentjabber import ProviderPersistentJabber

__all__ = ["ProviderDevelopergarden", "ProviderSipgate", "ProviderShell",
		"ProviderMock", "ProviderJabber", "ProviderMail"]

__all__.append("provider_drivers")
provider_drivers = dict(
		developergarden=ProviderDevelopergarden,
		sipgate=ProviderSipgate,
		shell=ProviderShell,
		mock=ProviderMock,
		jabber=ProviderJabber,
		mail=ProviderMail,
		persistentjabber=ProviderPersistentJabber)

