function diagnosePresentaton() {
  var pres = SlidesApp.openById('1wOYYbtIRdS8S5mydFIyDobS2pehvNHPR7GUK5PQYbeI');
  var slides = pres.getSlides();
  
  Logger.log('=== PRESENTATION DIAGNOSTIC ===');
  Logger.log('Total slides: ' + slides.length);
  Logger.log('');
  
  for (var i = 0; i < slides.length; i++) {
    var slide = slides[i];
    var elements = slide.getPageElements();
    
    Logger.log('--- SLIDE ' + (i + 1) + ' (ID: ' + slide.getObjectId() + ') ---');
    Logger.log('Layout: ' + slide.getLayout().getLayoutName());
    Logger.log('Elements: ' + elements.length);
    
    for (var j = 0; j < elements.length; j++) {
      var el = elements[j];
      var type = el.getPageElementType();
      
      if (type == SlidesApp.PageElementType.SHAPE) {
        var shape = el.asShape();
        var text = shape.getText().asString().trim();
        if (text.length > 0) {
          // Truncate long text for readability
          var preview = text.length > 200 ? text.substring(0, 200) + '...' : text;
          Logger.log('  [SHAPE ' + j + '] (ID: ' + el.getObjectId() + ') Text: ' + preview);
        }
      } else if (type == SlidesApp.PageElementType.TABLE) {
        var table = el.asTable();
        Logger.log('  [TABLE ' + j + '] (ID: ' + el.getObjectId() + ') Rows: ' + table.getNumRows() + ' Cols: ' + table.getNumColumns());
        // Log first row as header
        var headerText = [];
        for (var c = 0; c < table.getNumColumns(); c++) {
          headerText.push(table.getCell(0, c).getText().asString().trim());
        }
        Logger.log('    Headers: ' + headerText.join(' | '));
      } else if (type == SlidesApp.PageElementType.IMAGE) {
        Logger.log('  [IMAGE ' + j + '] (ID: ' + el.getObjectId() + ')');
      } else if (type == SlidesApp.PageElementType.GROUP) {
        Logger.log('  [GROUP ' + j + '] (ID: ' + el.getObjectId() + ') Children: ' + el.asGroup().getChildren().length);
      } else {
        Logger.log('  [' + type + ' ' + j + '] (ID: ' + el.getObjectId() + ')');
      }
    }
    Logger.log('');
  }
  
  Logger.log('=== END DIAGNOSTIC ===');
}
