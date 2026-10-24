# SDXorg interoperability fixtures

Unmodified XMILE definitions and Vensim reference CSVs from the SDXorg test-models collection, vendored through [Simlin commit 3f87e9024a580b86b65e3d0c5c3353660fc5426e](https://github.com/bpowers/simlin/tree/3f87e9024a580b86b65e3d0c5c3353660fc5426e/test/test-models/samples). The MIT license is retained in LICENSE. These are regression assets, not additions to the public model catalog.

- [Teacup provenance](https://github.com/bpowers/simlin/blob/3f87e9024a580b86b65e3d0c5c3353660fc5426e/test/test-models/samples/teacup/README.md): XMILE and output.csv by James Houghton, August 27, 2015; reference generated with Vensim DSS 6.3 for Mac.
- [SIR provenance](https://github.com/bpowers/simlin/blob/3f87e9024a580b86b65e3d0c5c3353660fc5426e/test/test-models/samples/SIR/README.md): XMILE by Bobby Powers, August 28, 2015 (xmileconv v0.1.0); output.csv by James Houghton, August 27, 2015 (Vensim DSS 6.3 for Mac).

Both contain an empty dimensions element despite being scalar models. Tests preserve the original inputs and compare every output column across the complete default horizon. The six-significant-digit reference exports require a tolerance (rtol 6e-6, atol 5e-6), not bit-for-bit comparison. SIR starts with susceptible=1000 and infectious=5; its actual compartment sum is 1005, while its force-of-infection denominator parameter is 1000. Preserve this upstream assumption when reproducing the benchmark; do not describe it as a calibrated epidemic forecast.
