from app.agent.tools.resume_parser import ResumeParserTool


def test_parse_detects_known_skills():
    parser = ResumeParserTool()
    result = parser.parse("Experienced with Python, SQL, AWS, and TensorFlow.")
    assert "Python" in result.skills
    assert "SQL" in result.skills
    assert "AWS" in result.skills
    assert "TensorFlow" in result.skills


def test_parse_extracts_experience_years():
    parser = ResumeParserTool()
    result = parser.parse("I have 5+ years of experience in backend development.")
    assert result.experience_years == 5


def test_parse_handles_empty_text():
    parser = ResumeParserTool()
    result = parser.parse("")
    assert result.skills == []
    assert result.experience_years is None


def test_parse_is_case_insensitive():
    parser = ResumeParserTool()
    result = parser.parse("I know REACT and docker very well.")
    assert "React" in result.skills
    assert "Docker" in result.skills
