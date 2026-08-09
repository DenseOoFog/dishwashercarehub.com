#!/usr/bin/env ruby

require "psych"

workflow_files = Dir[File.join(__dir__, "..", ".github", "workflows", "*.{yml,yaml}")].sort
abort "No GitHub Actions workflow files found." if workflow_files.empty?

workflow_files.each do |path|
  Psych.parse_file(path)
end

puts "Workflow YAML audit passed: #{workflow_files.length} files parsed successfully."
