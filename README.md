# phone-check
Checks mobile phone compatibility vs known-good database

## Canvas Hash Calibration

iPhones on iOS 12.2+ hide the GPU chip name from WebGL, returning "Apple GPU" instead. The calibration system uses canvas fingerprinting to map rendering hashes to GPU generations, enabling specific iPhone model detection even without direct GPU info.

See [doc/calibration.md](doc/calibration.md) for full details on how it works, how to run the BrowserStack probe, and how to manage the hash database.
