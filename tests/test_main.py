from linguaforge.main import main


def test_main(capsys):
    main()

    captured = capsys.readouterr()

    assert "LinguaForge 0.1.0" in captured.out
    assert "Sistema inicializado com sucesso." in captured.out
