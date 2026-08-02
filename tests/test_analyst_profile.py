"""Vérifie que le profil analyste projette son verdict en nœuds de trace."""

from intreepid.agent.analyst_profile import _record_verdict
from intreepid.agent.verdict import Observation


class _CapturingScribe:
    def __init__(self):
        self.specs = None

    def record_nodes(self, specs):
        self.specs = specs


def test_record_verdict_projects_observations_to_node_specs():
    sc = _CapturingScribe()
    _record_verdict(
        sc,  # type: ignore[arg-type]
        [
            Observation(
                claim="BE point noir", statut="fait", note="z=+34", confiance="haute"
            ),
            Observation(claim="baisse⇒sûr", statut="refusé", note="causalité"),
        ],
    )
    assert sc.specs == [
        (
            "observation",
            {"claim": "BE point noir", "note": "z=+34"},
            {"statut": "fait", "confiance": "haute", "nature": None},
        ),
        (
            "observation",
            {"claim": "baisse⇒sûr", "note": "causalité"},
            {"statut": "refusé", "confiance": None, "nature": None},
        ),
    ]


def test_record_verdict_none_scribe_is_noop():
    _record_verdict(None, [Observation(claim="c", statut="fait")])  # ne lève pas
