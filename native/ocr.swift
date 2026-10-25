// Local text recognition. No network access, files written, or third-party SDKs.
import Foundation
import Vision
import ImageIO

do {
    guard CommandLine.arguments.count == 2 else {
        throw NSError(domain: "AnkiStar", code: 1,
                      userInfo: [NSLocalizedDescriptionKey: "Choose one image file."])
    }
    let url = URL(fileURLWithPath: CommandLine.arguments[1])
    guard let imageSource = CGImageSourceCreateWithURL(url as CFURL, nil),
          CGImageSourceGetCount(imageSource) > 0 else {
        throw NSError(domain: "AnkiStar", code: 2,
                      userInfo: [NSLocalizedDescriptionKey: "This image could not be opened."])
    }
    let request = VNRecognizeTextRequest()
    request.recognitionLevel = .accurate
    request.usesLanguageCorrection = true
    request.automaticallyDetectsLanguage = true
    let handler = VNImageRequestHandler(url: url, options: [:])
    try handler.perform([request])
    let observations = request.results ?? []
    let lines = observations.compactMap { $0.topCandidates(1).first?.string }
    let data = try JSONSerialization.data(withJSONObject: ["text": lines.joined(separator: "\n")])
    FileHandle.standardOutput.write(data)
} catch {
    FileHandle.standardError.write(Data(error.localizedDescription.utf8))
    exit(1)
}
